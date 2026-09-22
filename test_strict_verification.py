import os
import sys
import unittest
from engine.job_searcher import job_searcher
from engine.matcher import matcher
from engine.verifier import verifier
from engine.applier import job_applier
from services.db import db

def test_job_discovery():
    print("\n--- Testing Open ATS Job Discovery ---")
    jobs = job_searcher.search_open_ats_jobs(limit=10)
    print(f"Discovered {len(jobs)} Open ATS jobs:")
    for j in jobs:
        score, _ = matcher.calculate_match_score(j)
        print(f"  [{score}%] {j.get('title')} at {j.get('company')} ({j.get('location')})")
        print(f"     URL: {j.get('job_url')}")
    assert len(jobs) > 0, "No jobs discovered from ATS boards"

def test_unsubmitted_page_rejection():
    print("\n--- Testing Strict Confirmation Rejection on Landing Page ---")
    # Simulate an unsubmitted landing page URL
    fake_job = {
        "job_id": "test_landing_page_check",
        "title": "Graduate Trainee",
        "company": "Test Corp",
        "location": "India",
        "portal": "Test Careers",
        "job_url": "https://www.google.com" # Generic page with no confirmation
    }
    success, msg, screenshot, ref_id = job_applier._apply_to_job(fake_job, 85)
    print(f"Result for unsubmitted page: success={success}, msg={msg}, screenshot={screenshot}")
    assert success is False, "Unsubmitted page was incorrectly marked as True!"
    assert screenshot is None, "Screenshot was incorrectly returned for unsubmitted page!"
    print("✅ Verified: Unsubmitted landing page was strictly rejected!")

if __name__ == "__main__":
    test_job_discovery()
    test_unsubmitted_page_rejection()
    print("\n🎉 All Verification Tests Passed Successfully!\n")
