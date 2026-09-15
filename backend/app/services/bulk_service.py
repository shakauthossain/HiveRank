import asyncio
import os
import uuid

import pandas as pd
from app.models import Audit, BulkJob, JobStatus
from app.services.analyze_deck import generate_analyze_deck
from app.services.seo_service import scrape_rankmath_async
from app.services.speed_service import fetch_pagespeed_data_sync, parse_pagespeed_data
from app.url_utils import is_valid_public_audit_url, normalize_url, resolved_url_for_storage
from sqlalchemy.orm import Session

REPORTS_DIR = os.path.join(os.getcwd(), "reports")
PAGESPEED_API_KEY = os.getenv("PAGESPEED_API_KEY")
BASE_URL = os.getenv("BASE_URL")
if BASE_URL:
    BASE_URL = BASE_URL.rstrip("/")


async def process_bulk_audit(db: Session, job_id: int, file_path: str, user_id: int):
    # Ensure columns exist in NeonDB (Safety check)
    try:
        from sqlalchemy import text
        db.execute(text("ALTER TABLE bulk_jobs ADD COLUMN IF NOT EXISTS total_count INTEGER DEFAULT 0;"))
        db.execute(text("ALTER TABLE bulk_jobs ADD COLUMN IF NOT EXISTS processed_count INTEGER DEFAULT 0;"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Migration check warning: {e}")

    job = db.query(BulkJob).filter(BulkJob.id == job_id).first()
    job.status = "running"
    db.commit()

    try:
        # Load file
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # Identify URL column
        url_col = None
        for col in df.columns:
            if col.lower() in ["url", "website", "link", "site"]:
                url_col = col
                break

        if not url_col:
            url_col = df.columns[0]  # Fallback to first column

        job.total_count = len(df)
        job.processed_count = 0
        db.commit()

        results = []

        for index, row in df.iterrows():
            result_row = row.to_dict()
            report_id = str(uuid.uuid4())

            url = normalize_url(str(row[url_col]).strip())
            ok, err_msg = is_valid_public_audit_url(url)
            if not ok:
                print(f"Skipping invalid URL ({index + 1}/{len(df)}): {url} — {err_msg}")
                result_row["Error Detail"] = err_msg
                result_row["SEO Score"] = "—"
                result_row["Speed M Score"] = "—"
                result_row["Speed D Score"] = "—"
                results.append(result_row)
                job.processed_count = index + 1
                db.commit()
                await asyncio.sleep(2)
                continue

            print(f"Processing ({index + 1}/{len(df)}): {url}")

            try:
                # 1. SEO
                seo_data = await scrape_rankmath_async(url)
                seo_score = seo_data.get("seo_score", "N/A")
                result_row["SEO Score"] = seo_score

                result_row["SEO Report Link"] = f"{BASE_URL}/reports/{report_id}_seo.html"

                # 2. Speed (with retry logic)
                speed_data = {}
                raw_mobile = None
                raw_desktop = None
                
                attempt = 0
                max_attempts = 2
                while attempt < max_attempts:
                    try:
                        print(f"Fetching Speed (M&D) for {url} (Attempt {attempt+1})")
                        mobile_t = asyncio.to_thread(fetch_pagespeed_data_sync, url, PAGESPEED_API_KEY, "mobile")
                        desktop_t = asyncio.to_thread(fetch_pagespeed_data_sync, url, PAGESPEED_API_KEY, "desktop")
                        raw_mobile, raw_desktop = await asyncio.gather(mobile_t, desktop_t)
                        if raw_mobile or raw_desktop:
                            break
                    except Exception as speed_e:
                        print(f"Speed fetch attempt {attempt+1} failed: {speed_e}")
                    
                    attempt += 1
                    if attempt < max_attempts:
                        await asyncio.sleep(2)

                speed_score_m = "N/A"
                speed_score_d = "N/A"

                if raw_mobile or raw_desktop:
                    mob_res = parse_pagespeed_data(raw_mobile, url, "mobile") if raw_mobile else {}
                    dsk_res = parse_pagespeed_data(raw_desktop, url, "desktop") if raw_desktop else {}
                    
                    speed_score_m = mob_res.get("perf_score", "N/A")
                    speed_score_d = dsk_res.get("perf_score", "N/A")
                    
                    speed_data = {
                        "mobile": mob_res,
                        "desktop": dsk_res,
                        "perf_score": speed_score_m,
                        "perf_score_desktop": speed_score_d
                    }
                    
                    result_row["Speed M Score"] = speed_score_m
                    result_row["Speed D Score"] = speed_score_d
                    result_row["Speed Report Link"] = f"{BASE_URL}/reports/{report_id}_speed.html"

                result_row["Speed Score"] = speed_score_m
                
                deck_html = generate_analyze_deck(seo_data, speed_data)
                h_path = os.path.join(REPORTS_DIR, f"{report_id}_seo.html")
                with open(h_path, "w", encoding="utf-8") as f:
                    f.write(deck_html)
                if speed_data:
                    h_path_speed = os.path.join(REPORTS_DIR, f"{report_id}_speed.html")
                    with open(h_path_speed, "w", encoding="utf-8") as f:
                        f.write(deck_html)

                stored_url = resolved_url_for_storage(url, speed_data)

                # Save to Database
                db_audit = Audit(
                    user_id=user_id,
                    url=stored_url,
                    seo_score=str(seo_score),
                    speed_score=f"M:{speed_score_m} D:{speed_score_d}",
                    report_id=report_id,
                    full_results={"seo": seo_data, "speed": speed_data},
                )
                db.add(db_audit)
                db.commit()

            except Exception as row_e:
                print(f"CRITICAL: Failed row {index} ({url}): {row_e}")
                result_row["SEO Score"] = result_row.get("SEO Score", "Error")
                result_row["Speed M Score"] = result_row.get("Speed M Score", "Error")
                result_row["Speed D Score"] = result_row.get("Speed D Score", "Error")
                result_row["Error Detail"] = str(row_e)

            results.append(result_row)
            
            # Update live progress
            job.processed_count = index + 1
            db.commit()
            
            await asyncio.sleep(2) # Safe buffer

        # Generate output file
        output_df = pd.DataFrame(results)
        output_filename = f"bulk_result_{job_id}.csv"
        output_path = os.path.join(REPORTS_DIR, output_filename)
        output_df.to_csv(output_path, index=False)

        job.status = "completed"
        job.output_filename = output_filename
        db.commit()

    except Exception as e:
        print(f"Bulk Error: {e}")
        job.status = "failed"
        db.commit()
