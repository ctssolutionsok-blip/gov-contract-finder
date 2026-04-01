import json
from db import init_db, get_connection

def refresh_sam_data():
    sample_rows = [
        {
            "notice_id": "TEST123",
            "title": "Sample Opportunity",
            "agency": "Department of Example",
            "notice_type": "Sources Sought",
            "set_aside": "8(a)",
            "naics_code": "541611",
            "response_date": "2026-03-30",
            "state": "OK",
            "url": "https://example.com",
            "posted_date": "2026-03-30",
            "raw_json": json.dumps({"sample": True})
        }
    ]

    conn = get_connection()
    cur = conn.cursor()

    for row in sample_rows:
        cur.execute("""
        INSERT OR REPLACE INTO sam_opportunities
        (notice_id, title, agency, notice_type, set_aside, naics_code, response_date, state, url, posted_date, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["notice_id"],
            row["title"],
            row["agency"],
            row["notice_type"],
            row["set_aside"],
            row["naics_code"],
            row["response_date"],
            row["state"],
            row["url"],
            row["posted_date"],
            row["raw_json"]
        ))

    conn.commit()
    conn.close()

def refresh_usaspending_data():
    sample_rows = [
        {
            "award_id": "AWARD123",
            "recipient_name": "Example Contractor LLC",
            "awarding_agency": "Department of Example",
            "naics_code": "541611",
            "award_amount": 250000.00,
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "place_of_performance": "Oklahoma",
            "raw_json": json.dumps({"sample": True})
        }
    ]

    conn = get_connection()
    cur = conn.cursor()

    for row in sample_rows:
        cur.execute("""
        INSERT OR REPLACE INTO usaspending_awards
        (award_id, recipient_name, awarding_agency, naics_code, award_amount, start_date, end_date, place_of_performance, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row["award_id"],
            row["recipient_name"],
            row["awarding_agency"],
            row["naics_code"],
            row["award_amount"],
            row["start_date"],
            row["end_date"],
            row["place_of_performance"],
            row["raw_json"]
        ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    refresh_sam_data()
    refresh_usaspending_data()
    print("Database refresh complete.")