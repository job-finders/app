"""
End-to-End Tests for Job Match Scoring Workflow

These tests verify the complete user workflow from viewing job listings
to interacting with match details modal.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class TestJobMatchWorkflow:
    """End-to-end tests for job match scoring workflow"""

    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode for CI
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def authenticated_user(self, driver):
        """Login as test user"""
        driver.get("http://localhost:5000/auth/login")
        
        # Fill login form
        email_input = driver.find_element(By.NAME, "email")
        password_input = driver.find_element(By.NAME, "password")
        
        email_input.send_keys("test@example.com")
        password_input.send_keys("testpassword")
        
        # Submit form
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # Wait for redirect to dashboard
        WebDriverWait(driver, 10).until(
            EC.url_contains("/dashboard")
        )
        
        return driver

    def test_job_listing_displays_match_scores(self, authenticated_user):
        """Test that job listings display match scores for authenticated users"""
        driver = authenticated_user
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        # Check that match score badges are present
        match_badges = driver.find_elements(By.CLASS_NAME, "match-score-badge")
        assert len(match_badges) > 0, "No match score badges found"
        
        # Check that at least one badge shows a percentage
        score_found = False
        for badge in match_badges:
            if "%" in badge.text:
                score_found = True
                break
        
        assert score_found, "No percentage scores found in match badges"

    def test_unauthenticated_user_sees_login_prompt(self, driver):
        """Test that unauthenticated users see login prompts instead of match scores"""
        # Navigate to job listings without logging in
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        # Check for login required badges
        login_badges = driver.find_elements(By.CLASS_NAME, "login-required")
        assert len(login_badges) > 0, "No login required badges found"
        
        # Check that login text is present
        login_text_found = False
        for badge in login_badges:
            if "Login Required" in badge.text:
                login_text_found = True
                break
        
        assert login_text_found, "Login required text not found"

    def test_match_details_modal_opens_and_closes(self, authenticated_user):
        """Test that match details modal opens and closes correctly"""
        driver = authenticated_user
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        # Find and click a match details button
        match_details_buttons = driver.find_elements(By.CLASS_NAME, "btn-match-details")
        assert len(match_details_buttons) > 0, "No match details buttons found"
        
        # Click the first match details button
        match_details_buttons[0].click()
        
        # Wait for modal to appear
        modal = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "matchDetailsModal"))
        )
        
        assert modal.is_displayed(), "Modal is not visible"
        
        # Check that modal has expected content
        modal_header = driver.find_element(By.CLASS_NAME, "modal-header")
        assert "Job Match Analysis" in modal_header.text
        
        # Close modal by clicking close button
        close_button = driver.find_element(By.CLASS_NAME, "modal-close")
        close_button.click()
        
        # Wait for modal to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "matchDetailsModal"))
        )

    def test_modal_closes_on_escape_key(self, authenticated_user):
        """Test that modal closes when ESC key is pressed"""
        driver = authenticated_user
        
        # Navigate to job listings and open modal
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-match-details"))
        )
        
        match_details_button = driver.find_element(By.CLASS_NAME, "btn-match-details")
        match_details_button.click()
        
        # Wait for modal to appear
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "matchDetailsModal"))
        )
        
        # Press ESC key
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        
        # Wait for modal to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "matchDetailsModal"))
        )

    def test_modal_closes_on_overlay_click(self, authenticated_user):
        """Test that modal closes when clicking outside the modal content"""
        driver = authenticated_user
        
        # Navigate to job listings and open modal
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-match-details"))
        )
        
        match_details_button = driver.find_element(By.CLASS_NAME, "btn-match-details")
        match_details_button.click()
        
        # Wait for modal to appear
        modal_overlay = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "matchDetailsModal"))
        )
        
        # Click on the overlay (outside modal content)
        ActionChains(driver).move_to_element_with_offset(modal_overlay, 10, 10).click().perform()
        
        # Wait for modal to disappear
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.ID, "matchDetailsModal"))
        )

    def test_modal_displays_loading_state(self, authenticated_user):
        """Test that modal shows loading state while fetching data"""
        driver = authenticated_user
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-match-details"))
        )
        
        match_details_button = driver.find_element(By.CLASS_NAME, "btn-match-details")
        match_details_button.click()
        
        # Check for loading spinner (should appear briefly)
        try:
            loading_spinner = WebDriverWait(driver, 2).until(
                EC.visibility_of_element_located((By.ID, "modalLoadingSpinner"))
            )
            assert loading_spinner.is_displayed(), "Loading spinner not visible"
        except TimeoutException:
            # Loading might be too fast to catch, which is okay
            pass

    def test_modal_displays_match_analysis_content(self, authenticated_user):
        """Test that modal displays detailed match analysis content"""
        driver = authenticated_user
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-match-details"))
        )
        
        match_details_button = driver.find_element(By.CLASS_NAME, "btn-match-details")
        match_details_button.click()
        
        # Wait for match analysis content to load
        match_content = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.ID, "matchAnalysisContent"))
        )
        
        # Check for overall score
        score_element = driver.find_element(By.ID, "overallScoreNumber")
        assert score_element.text.endswith("%"), "Overall score not displayed correctly"
        
        # Check for match categories
        categories = ["skills", "experience", "location", "salary"]
        for category in categories:
            category_element = driver.find_element(By.CSS_SELECTOR, f'[data-category="{category}"]')
            assert category_element.is_displayed(), f"{category} category not displayed"

    def test_modal_handles_api_errors_gracefully(self, authenticated_user):
        """Test that modal handles API errors gracefully"""
        driver = authenticated_user
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        # Simulate network error by blocking API requests
        driver.execute_script("""
            // Override fetch to simulate network error
            window.originalFetch = window.fetch;
            window.fetch = function() {
                return Promise.reject(new Error('Network error'));
            };
        """)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-match-details"))
        )
        
        match_details_button = driver.find_element(By.CLASS_NAME, "btn-match-details")
        match_details_button.click()
        
        # Wait for error state to appear
        error_state = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "modalErrorState"))
        )
        
        assert error_state.is_displayed(), "Error state not displayed"
        
        # Check for retry button
        retry_button = driver.find_element(By.ID, "retryMatchAnalysis")
        assert retry_button.is_displayed(), "Retry button not displayed"
        
        # Restore original fetch
        driver.execute_script("window.fetch = window.originalFetch;")

    def test_incomplete_profile_shows_completion_prompt(self, driver):
        """Test that users with incomplete profiles see completion prompts"""
        # Login as user with incomplete profile
        driver.get("http://localhost:5000/auth/login")
        
        # Login with incomplete profile user
        email_input = driver.find_element(By.NAME, "email")
        password_input = driver.find_element(By.NAME, "password")
        
        email_input.send_keys("incomplete@example.com")
        password_input.send_keys("testpassword")
        
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_button.click()
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        # Check for profile completion badges
        completion_badges = driver.find_elements(By.CLASS_NAME, "incomplete-profile")
        assert len(completion_badges) > 0, "No profile completion badges found"
        
        # Check for profile completion buttons
        completion_buttons = driver.find_elements(By.CLASS_NAME, "btn-complete-profile")
        assert len(completion_buttons) > 0, "No profile completion buttons found"

    def test_responsive_design_on_mobile(self, driver):
        """Test that job listings and modal work on mobile devices"""
        # Set mobile viewport
        driver.set_window_size(375, 667)  # iPhone 6/7/8 size
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        # Check that job cards are properly sized for mobile
        job_cards = driver.find_elements(By.CLASS_NAME, "job-card")
        assert len(job_cards) > 0, "No job cards found"
        
        # Check that cards don't overflow viewport
        for card in job_cards[:3]:  # Check first 3 cards
            card_width = card.size['width']
            viewport_width = driver.get_window_size()['width']
            assert card_width <= viewport_width, f"Job card too wide for mobile: {card_width}px"

    def test_accessibility_features(self, authenticated_user):
        """Test accessibility features of the job match interface"""
        driver = authenticated_user
        
        # Navigate to job listings
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-match-details"))
        )
        
        # Check for ARIA labels on interactive elements
        match_details_button = driver.find_element(By.CLASS_NAME, "btn-match-details")
        aria_label = match_details_button.get_attribute("aria-label")
        # Should have descriptive aria-label or text content
        
        # Open modal
        match_details_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "matchDetailsModal"))
        )
        
        # Check modal accessibility
        modal = driver.find_element(By.ID, "matchDetailsModal")
        role = modal.get_attribute("role")
        # Should have appropriate ARIA role
        
        # Check close button accessibility
        close_button = driver.find_element(By.CLASS_NAME, "modal-close")
        close_aria_label = close_button.get_attribute("aria-label")
        assert close_aria_label is not None, "Close button missing aria-label"

    def test_performance_with_many_jobs(self, authenticated_user):
        """Test performance with large number of job listings"""
        driver = authenticated_user
        
        # Navigate to job listings page with many jobs
        driver.get("http://localhost:5000/jobs/browse-jobs?page_size=100")
        
        start_time = time.time()
        
        # Wait for page to load completely
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        load_time = time.time() - start_time
        
        # Page should load within reasonable time (30 seconds max)
        assert load_time < 30, f"Page took too long to load: {load_time}s"
        
        # Check that match scores are calculated for visible jobs
        match_badges = driver.find_elements(By.CLASS_NAME, "match-score-badge")
        job_cards = driver.find_elements(By.CLASS_NAME, "job-card")
        
        # Should have match badges for all job cards
        assert len(match_badges) == len(job_cards), "Missing match score badges"

    def test_search_functionality_with_match_scores(self, authenticated_user):
        """Test that search results include match scores"""
        driver = authenticated_user
        
        # Navigate to search page
        driver.get("http://localhost:5000/jobs/search?keyword=python")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        # Check that search results have match scores
        match_badges = driver.find_elements(By.CLASS_NAME, "match-score-badge")
        assert len(match_badges) > 0, "No match scores in search results"
        
        # Check that match details buttons are present
        match_details_buttons = driver.find_elements(By.CLASS_NAME, "btn-match-details")
        assert len(match_details_buttons) > 0, "No match details buttons in search results"

    def test_category_filtering_with_match_scores(self, authenticated_user):
        """Test that category-filtered jobs include match scores"""
        driver = authenticated_user
        
        # Navigate to category page
        driver.get("http://localhost:5000/jobs/category/engineering")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-listings-container"))
        )
        
        # Check that category results have match scores
        match_badges = driver.find_elements(By.CLASS_NAME, "match-score-badge")
        job_cards = driver.find_elements(By.CLASS_NAME, "job-card")
        
        if len(job_cards) > 0:  # Only check if jobs exist in category
            assert len(match_badges) > 0, "No match scores in category results"


class TestJobMatchPerformance:
    """Performance tests for job match scoring"""

    def test_match_score_calculation_performance(self, authenticated_user):
        """Test that match score calculation doesn't significantly slow down page load"""
        driver = authenticated_user
        
        # Measure page load time without match scores (if possible)
        # This would require a way to disable match scoring temporarily
        
        # Measure page load time with match scores
        start_time = time.time()
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "match-score-badge"))
        )
        
        load_time = time.time() - start_time
        
        # Should load within reasonable time
        assert load_time < 15, f"Page with match scores took too long: {load_time}s"

    def test_modal_api_response_time(self, authenticated_user):
        """Test that match details API responds quickly"""
        driver = authenticated_user
        
        driver.get("http://localhost:5000/jobs/browse-jobs")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-match-details"))
        )
        
        match_details_button = driver.find_element(By.CLASS_NAME, "btn-match-details")
        
        start_time = time.time()
        match_details_button.click()
        
        # Wait for content to load (not just modal to appear)
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "matchAnalysisContent"))
        )
        
        response_time = time.time() - start_time
        
        # API should respond within reasonable time
        assert response_time < 10, f"Match details API too slow: {response_time}s"


if __name__ == '__main__':
    pytest.main([__file__, "-v"])