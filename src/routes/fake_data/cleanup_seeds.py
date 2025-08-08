import os

files_to_remove = [
    'seeds/fake_job_controller.py',
    'seeds/fake_job_applications.py', 
    'seeds/fake_jobseeker_profile.py',
    'seeds/fake_resume.py',
    'seeds/fake_ats_report.py'
]

for file in files_to_remove:
    try:
        os.remove(file)
        print(f"Removed: {file}")
    except FileNotFoundError:
        print(f"File not found: {file}")
    except Exception as e:
        print(f"Error removing {file}: {str(e)}")

print("Cleanup complete")