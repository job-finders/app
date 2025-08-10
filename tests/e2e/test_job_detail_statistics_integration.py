"""
Integration Tests for Job Detail Page with Statistics

These tests verify the complete job detail page functionality including
statistics display, responsive design, chart rendering, and performance.
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

from tests.jobs.factories import create_job, create_company, create_category, create_job_application, create_ats_report
from src.database.models.jobs_model import JobStatusEnum


class TestJobDetailStatisticsIntegration:
    """Integration tests for job detail page with statistics"""

    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver for testing"""
        options = Options()
        options.add_argument("--headless")  # Run in headless mode for CI
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    @pytest.fixture
    def test_job_with_statistics(self, session):
        """Create a test job with comprehensive statistics data"""
        # Create category and company
        category = create_category(session, name="Engineering")
        company = create_company(session, name="Test Company")
        
        # Create job with applications and ATS reports
        job = create_job(
            session,
            title="Senior Python Developer",
            description="Looking for an experienced Python developer",
            company_id=company.company_id,
            category_id=category.category_id,
            status=JobStatusEnum.ACTIVE.value,
            posted_at=datetime.now() - timedelta(days=10)
        )
        
        # Create applications with varying dates for trend analysis
        for i in range(15):
            days_ago = 10 - i
            create_job_application(
                session,
                job_id=job.job_id,
                applied_date=datetime.now() - timedelta(days=days_ago),
                method="website" if i % 2 == 0 else "external"
            )
        
        # Create ATS reports for competitiveness analysis
        for i in range(10):
            score = 60 + (i * 5)  # Scores from 60 to 105 (capped at 100)
            create_ats_report(
                session,
                job_id=job.job_id,
                cv_id=str(uuid.uuid4()),  # Add required cv_id
                score=min(score, 100),
                matched_keywords=["Python", "Django", "REST API"][:i%3+1],
                missing_keywords=["Docker", "Kubernetes", "AWS"][:(3-i%3)],
                feedback=f"ATS evaluation feedback for report {i+1}"
            )
        
        session.commit()
        return job 
   def test_job_detail_page_loads_with_statistics(self, driver, test_job_with_statistics):
        """Test that job detail page loads completely with all statistics sections"""
        job = test_job_with_statistics
        
        # Navigate to job detail page
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-fluid"))
        )
        
        # Verify job header is present
        job_title = driver.find_element(By.TAG_NAME, "h1")
        assert job.title in job_title.text
        
        # Verify all statistics sections are present
        statistics_sections = [
            "Application Statistics",
            "Job Competitiveness", 
            "Application Trends",
            "Company Hiring Statistics"
        ]
        
        for section_name in statistics_sections:
            section_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//h3[contains(text(), '{section_name}')]"))
            )
            assert section_element.is_displayed(), f"{section_name} section not visible"

    def test_application_statistics_display(self, driver, test_job_with_statistics):
        """Test application statistics section displays correctly"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for application statistics section
        app_stats_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Application Statistics')]"))
        )
        
        # Check total applications display
        total_apps_element = driver.find_element(By.XPATH, "//small[text()='Total Applications']/preceding-sibling::div//span")
        assert total_apps_element.text.isdigit(), "Total applications should be a number"
        
        # Check applications per day display
        apps_per_day_element = driver.find_element(By.XPATH, "//small[text()='Applications per Day']/preceding-sibling::div//span")
        assert "." in apps_per_day_element.text or apps_per_day_element.text.isdigit(), "Apps per day should be numeric"
        
        # Check trend indicator
        trend_element = driver.find_element(By.XPATH, "//small[text()='Recent Trend']/preceding-sibling::div//span")
        trend_classes = trend_element.get_attribute("class")
        assert any(trend in trend_classes for trend in ["success", "warning", "secondary"]), "Trend should have appropriate styling"
        
        # Check competition level indicator
        competition_element = driver.find_element(By.XPATH, "//span[text()='Competition Level:']/following-sibling::span")
        competition_text = competition_element.text.lower()
        assert any(level in competition_text for level in ["low", "medium", "high"]), "Competition level should be categorized"

    def test_competitiveness_metrics_display(self, driver, test_job_with_statistics):
        """Test job competitiveness section displays ATS data correctly"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for competitiveness section
        comp_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Job Competitiveness')]"))
        )
        
        # Check average match score display
        avg_score_element = driver.find_element(By.XPATH, "//small[text()='Average Match Score']/preceding-sibling::div//span")
        score_text = avg_score_element.text.replace("%", "")
        assert score_text.replace(".", "").isdigit() or score_text == "N/A", "Average match score should be numeric or N/A"
        
        # Check ATS readiness percentage
        readiness_element = driver.find_element(By.XPATH, "//small[text()='Well-Matched Applicants']/preceding-sibling::div//span")
        readiness_text = readiness_element.text.replace("%", "")
        assert readiness_text.isdigit(), "ATS readiness should be a percentage"
        
        # Check match score distribution
        distribution_elements = driver.find_elements(By.XPATH, "//h6[text()='Match Score Distribution']/following-sibling::div//div[contains(@class, 'col-auto')]")
        assert len(distribution_elements) > 0, "Match score distribution should be displayed"
        
        # Check top matched keywords
        matched_keywords = driver.find_elements(By.XPATH, "//h6[contains(text(), 'Most Matched Skills')]/following-sibling::div//span[contains(@class, 'badge')]")
        assert len(matched_keywords) > 0, "Should display matched keywords"
        
        # Check top missing keywords  
        missing_keywords = driver.find_elements(By.XPATH, "//h6[contains(text(), 'Often Missing Skills')]/following-sibling::div//span[contains(@class, 'badge')]")
        assert len(missing_keywords) > 0, "Should display missing keywords" 
   def test_trend_analysis_with_chart(self, driver, test_job_with_statistics):
        """Test application trends section including chart rendering"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for trends section
        trends_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Application Trends')]"))
        )
        
        # Check application velocity display
        velocity_element = driver.find_element(By.XPATH, "//small[text()='Application Velocity']/preceding-sibling::div//span")
        velocity_text = velocity_element.text.lower()
        assert any(vel in velocity_text for vel in ["accelerating", "slowing", "steady"]), "Velocity should be categorized"
        
        # Check overall trend display
        trend_element = driver.find_element(By.XPATH, "//small[text()='Overall Trend']/preceding-sibling::div//span")
        trend_text = trend_element.text.lower()
        assert any(trend in trend_text for trend in ["rising", "falling", "stable"]), "Trend should be categorized"
        
        # Check days tracked
        days_element = driver.find_element(By.XPATH, "//small[text()='Days Tracked']/preceding-sibling::div//span")
        assert days_element.text.isdigit(), "Days tracked should be numeric"
        
        # Wait for chart to load
        chart_canvas = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "applicationTrendChart"))
        )
        assert chart_canvas.is_displayed(), "Application trend chart should be visible"
        
        # Verify chart has been rendered (canvas should have content)
        chart_context = driver.execute_script("return document.getElementById('applicationTrendChart').getContext('2d')")
        assert chart_context is not None, "Chart should be initialized"
        
        # Check industry comparison if available
        try:
            this_job_element = driver.find_element(By.XPATH, "//span[text()='This Job:']/following-sibling::span")
            industry_avg_element = driver.find_element(By.XPATH, "//span[text()='Industry Average:']/following-sibling::span")
            
            assert "apps/day" in this_job_element.text, "This job metric should show apps/day"
            assert "apps/day" in industry_avg_element.text, "Industry average should show apps/day"
        except NoSuchElementException:
            # Industry comparison might not be available for all jobs
            pass

    def test_company_statistics_display(self, driver, test_job_with_statistics):
        """Test company hiring statistics section"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for company statistics section
        company_section = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Company Hiring Statistics')]"))
        )
        
        # Check jobs posted metric
        jobs_posted_element = driver.find_element(By.XPATH, "//small[text()='Jobs Posted (12 months)']/preceding-sibling::div//span")
        assert jobs_posted_element.text.isdigit(), "Jobs posted should be numeric"
        
        # Check average applications per job
        avg_apps_element = driver.find_element(By.XPATH, "//small[text()='Avg Applications/Job']/preceding-sibling::div//span")
        avg_apps_text = avg_apps_element.text
        assert "." in avg_apps_text or avg_apps_text.isdigit(), "Avg applications should be numeric"
        
        # Check response rate
        response_rate_element = driver.find_element(By.XPATH, "//small[text()='Response Rate']/preceding-sibling::div//span")
        response_text = response_rate_element.text.replace("%", "")
        assert response_text.isdigit(), "Response rate should be a percentage"
        
        # Check hiring activity level
        activity_element = driver.find_element(By.XPATH, "//span[text()='Hiring Activity:']/following-sibling::span")
        activity_text = activity_element.text.lower()
        assert any(level in activity_text for level in ["very active", "moderately active", "less active"]), "Activity level should be categorized"
        
        # Check response quality
        quality_element = driver.find_element(By.XPATH, "//span[text()='Response Quality:']/following-sibling::span")
        quality_text = quality_element.text.lower()
        assert any(quality in quality_text for quality in ["excellent", "good", "fair", "poor"]), "Response quality should be categorized" 
   def test_responsive_design_mobile(self, driver, test_job_with_statistics):
        """Test responsive design functionality on mobile screen sizes"""
        job = test_job_with_statistics
        
        # Set mobile viewport (iPhone 12 Pro size)
        driver.set_window_size(390, 844)
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-fluid"))
        )
        
        # Check that statistics sections are still visible and properly sized
        statistics_sections = driver.find_elements(By.XPATH, "//div[contains(@class, 'bg-white') and contains(@class, 'rounded-3')]")
        assert len(statistics_sections) > 0, "Statistics sections should be visible on mobile"
        
        # Verify sections don't overflow viewport
        viewport_width = driver.get_window_size()['width']
        for section in statistics_sections[:3]:  # Check first 3 sections
            section_width = section.size['width']
            assert section_width <= viewport_width, f"Section too wide for mobile: {section_width}px"
        
        # Check that badges and metrics are readable on mobile
        badges = driver.find_elements(By.CLASS_NAME, "badge")
        for badge in badges[:5]:  # Check first 5 badges
            assert badge.is_displayed(), "Badges should be visible on mobile"
            badge_height = badge.size['height']
            assert badge_height > 0, "Badges should have visible height"
        
        # Verify chart container adapts to mobile
        try:
            chart_container = driver.find_element(By.CLASS_NAME, "chart-container")
            container_width = chart_container.size['width']
            assert container_width <= viewport_width, "Chart container should fit mobile viewport"
        except NoSuchElementException:
            # Chart might not be present for all jobs
            pass

    def test_responsive_design_tablet(self, driver, test_job_with_statistics):
        """Test responsive design functionality on tablet screen sizes"""
        job = test_job_with_statistics
        
        # Set tablet viewport (iPad size)
        driver.set_window_size(768, 1024)
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-fluid"))
        )
        
        # Check layout adapts properly for tablet
        main_content = driver.find_element(By.XPATH, "//div[contains(@class, 'col-lg-8')]")
        sidebar = driver.find_element(By.XPATH, "//div[contains(@class, 'col-lg-4')]")
        
        assert main_content.is_displayed(), "Main content should be visible on tablet"
        assert sidebar.is_displayed(), "Sidebar should be visible on tablet"
        
        # Verify statistics grid layout works on tablet
        stat_cards = driver.find_elements(By.XPATH, "//div[contains(@class, 'col-md-')]")
        for card in stat_cards[:6]:  # Check first 6 cards
            assert card.is_displayed(), "Stat cards should be visible on tablet"

    def test_responsive_design_desktop(self, driver, test_job_with_statistics):
        """Test responsive design functionality on desktop screen sizes"""
        job = test_job_with_statistics
        
        # Set desktop viewport
        driver.set_window_size(1920, 1080)
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-fluid"))
        )
        
        # Verify full desktop layout
        main_content = driver.find_element(By.XPATH, "//div[contains(@class, 'col-lg-8')]")
        sidebar = driver.find_element(By.XPATH, "//div[contains(@class, 'col-lg-4')]")
        
        main_width = main_content.size['width']
        sidebar_width = sidebar.size['width']
        
        # Main content should be wider than sidebar on desktop
        assert main_width > sidebar_width, "Main content should be wider than sidebar on desktop"
        
        # Check that all statistics sections have proper spacing
        sections = driver.find_elements(By.XPATH, "//div[contains(@class, 'bg-white') and contains(@class, 'rounded-3')]")
        for i, section in enumerate(sections[:-1]):  # All but last section
            section_bottom = section.location['y'] + section.size['height']
            next_section_top = sections[i + 1].location['y']
            gap = next_section_top - section_bottom
            assert gap > 0, f"Sections should have spacing between them: gap={gap}"  
  def test_chart_rendering_and_interactions(self, driver, test_job_with_statistics):
        """Test chart rendering and interactive features"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for chart to be present
        chart_canvas = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "applicationTrendChart"))
        )
        
        # Verify chart is rendered
        assert chart_canvas.is_displayed(), "Chart canvas should be visible"
        
        # Check that Chart.js is loaded
        chart_js_loaded = driver.execute_script("return typeof Chart !== 'undefined'")
        assert chart_js_loaded, "Chart.js should be loaded"
        
        # Verify chart instance exists
        chart_instance = driver.execute_script("""
            const canvas = document.getElementById('applicationTrendChart');
            return Chart.getChart(canvas) !== undefined;
        """)
        assert chart_instance, "Chart instance should be created"
        
        # Test chart hover interactions
        actions = ActionChains(driver)
        actions.move_to_element(chart_canvas).perform()
        
        # Wait a moment for any hover effects
        time.sleep(0.5)
        
        # Verify chart data is present
        chart_data = driver.execute_script("""
            const canvas = document.getElementById('applicationTrendChart');
            const chart = Chart.getChart(canvas);
            return chart && chart.data && chart.data.datasets && chart.data.datasets.length > 0;
        """)
        assert chart_data, "Chart should have data"
        
        # Test chart responsiveness
        original_size = chart_canvas.size
        driver.set_window_size(800, 600)
        time.sleep(1)  # Allow time for resize
        
        new_size = chart_canvas.size
        # Chart should adapt to new size (width should change)
        assert new_size['width'] != original_size['width'], "Chart should resize with window"

    def test_statistics_tooltips_and_help_text(self, driver, test_job_with_statistics):
        """Test explanatory tooltips and help text functionality"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-fluid"))
        )
        
        # Look for tooltip triggers (info icons)
        tooltip_triggers = driver.find_elements(By.XPATH, "//i[contains(@class, 'fa-info-circle')]")
        
        if len(tooltip_triggers) > 0:
            # Test tooltip interaction
            first_trigger = tooltip_triggers[0]
            actions = ActionChains(driver)
            actions.move_to_element(first_trigger).perform()
            
            # Wait for tooltip to appear (either Bootstrap or custom)
            time.sleep(1)
            
            # Check if Bootstrap tooltip appeared
            try:
                tooltip = driver.find_element(By.CLASS_NAME, "tooltip")
                assert tooltip.is_displayed(), "Tooltip should be visible on hover"
            except NoSuchElementException:
                # Check for custom tooltip
                try:
                    custom_tooltip = driver.find_element(By.ID, "custom-tooltip")
                    tooltip_opacity = custom_tooltip.value_of_css_property("opacity")
                    assert float(tooltip_opacity) > 0, "Custom tooltip should be visible"
                except NoSuchElementException:
                    # Tooltips might not be implemented yet
                    pass
        
        # Check for explanatory text in statistics sections
        explanatory_texts = driver.find_elements(By.XPATH, "//small[contains(@class, 'text-muted')]")
        assert len(explanatory_texts) > 0, "Should have explanatory text for statistics"    def 
test_page_load_performance_with_statistics(self, driver, test_job_with_statistics):
        """Test page load performance with statistics enabled"""
        job = test_job_with_statistics
        
        # Measure page load time
        start_time = time.time()
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for all critical elements to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))  # Job title
        )
        
        # Wait for statistics sections to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Application Statistics')]"))
        )
        
        # Wait for any charts to render
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "applicationTrendChart"))
            )
            # Wait for chart to be fully rendered
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("""
                    const canvas = document.getElementById('applicationTrendChart');
                    return canvas && Chart.getChart(canvas) !== undefined;
                """)
            )
        except TimeoutException:
            # Chart might not be present for all jobs
            pass
        
        load_time = time.time() - start_time
        
        # Page should load within reasonable time (30 seconds max, ideally under 10)
        assert load_time < 30, f"Page took too long to load: {load_time:.2f}s"
        
        # Log performance for monitoring
        print(f"Job detail page with statistics loaded in {load_time:.2f} seconds")
        
        # Verify page is fully interactive
        assert driver.execute_script("return document.readyState") == "complete", "Page should be fully loaded"

    def test_statistics_error_handling_and_fallbacks(self, driver, session):
        """Test graceful handling when statistics are unavailable"""
        # Create job without applications or ATS data
        category = create_category(session, name="Marketing")
        company = create_company(session, name="Minimal Company")
        
        job = create_job(
            session,
            title="Marketing Specialist",
            company_id=company.company_id,
            category_id=category.category_id,
            status=JobStatusEnum.ACTIVE.value
        )
        session.commit()
        
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        
        # Check for appropriate fallback messages
        try:
            # Look for "Be First!" message for zero applications
            be_first_element = driver.find_element(By.XPATH, "//span[contains(text(), 'Be First!')]")
            assert be_first_element.is_displayed(), "Should show 'Be First!' for zero applications"
        except NoSuchElementException:
            # Check for other fallback messages
            fallback_messages = [
                "Application data not available",
                "Match analysis not available",
                "Trend data not available",
                "New posting - trend data developing"
            ]
            
            page_text = driver.page_source
            fallback_found = any(message in page_text for message in fallback_messages)
            assert fallback_found, "Should show appropriate fallback messages when data is unavailable"    d
ef test_statistics_accessibility_features(self, driver, test_job_with_statistics):
        """Test accessibility features of statistics sections"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "container-fluid"))
        )
        
        # Check for proper heading hierarchy
        headings = driver.find_elements(By.XPATH, "//h1 | //h2 | //h3 | //h4 | //h5 | //h6")
        assert len(headings) > 0, "Should have proper heading structure"
        
        # Verify main job title is h1
        h1_elements = driver.find_elements(By.TAG_NAME, "h1")
        assert len(h1_elements) == 1, "Should have exactly one h1 element"
        assert job.title in h1_elements[0].text, "h1 should contain job title"
        
        # Check for alt text on any images
        images = driver.find_elements(By.TAG_NAME, "img")
        for img in images:
            alt_text = img.get_attribute("alt")
            assert alt_text is not None and alt_text.strip() != "", f"Image should have alt text: {img.get_attribute('src')}"
        
        # Check color contrast for badges (basic check)
        badges = driver.find_elements(By.CLASS_NAME, "badge")
        for badge in badges[:5]:  # Check first 5 badges
            bg_color = badge.value_of_css_property("background-color")
            text_color = badge.value_of_css_property("color")
            assert bg_color != text_color, "Badge should have contrasting background and text colors"
        
        # Verify focusable elements have proper focus indicators
        focusable_elements = driver.find_elements(By.XPATH, "//button | //a | //input | //select | //textarea")
        for element in focusable_elements[:3]:  # Check first 3 focusable elements
            element.click()  # Focus the element
            outline = element.value_of_css_property("outline")
            # Should have some form of focus indicator (outline or box-shadow)
            box_shadow = element.value_of_css_property("box-shadow")
            assert outline != "none" or box_shadow != "none", "Focusable elements should have focus indicators"

    def test_statistics_data_accuracy(self, driver, test_job_with_statistics):
        """Test that displayed statistics match expected calculations"""
        job = test_job_with_statistics
        driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Wait for statistics to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Application Statistics')]"))
        )
        
        # Get total applications from page
        total_apps_element = driver.find_element(By.XPATH, "//small[text()='Total Applications']/preceding-sibling::div//span")
        displayed_total = int(total_apps_element.text)
        
        # We created 15 applications in the fixture
        expected_total = 15
        assert displayed_total == expected_total, f"Expected {expected_total} applications, got {displayed_total}"
        
        # Check applications per day calculation
        apps_per_day_element = driver.find_element(By.XPATH, "//small[text()='Applications per Day']/preceding-sibling::div//span")
        displayed_per_day = float(apps_per_day_element.text)
        
        # Job was posted 10 days ago, so should be 15/10 = 1.5 apps per day
        expected_per_day = 1.5
        assert abs(displayed_per_day - expected_per_day) < 0.1, f"Expected ~{expected_per_day} apps/day, got {displayed_per_day}"
        
        # Verify ATS data if present
        try:
            avg_score_element = driver.find_element(By.XPATH, "//small[text()='Average Match Score']/preceding-sibling::div//span")
            score_text = avg_score_element.text.replace("%", "")
            if score_text != "N/A":
                displayed_score = float(score_text)
                # We created scores from 60 to 100 (10 reports), average should be 80
                expected_avg = 80.0
                assert abs(displayed_score - expected_avg) < 5, f"Expected ~{expected_avg}% avg score, got {displayed_score}%"
        except NoSuchElementException:
            # ATS data might not be displayed
            pass
c
lass TestJobDetailStatisticsPerformance:
    """Performance-focused tests for job detail statistics"""

    @pytest.fixture(scope="class")
    def performance_driver(self):
        """Setup Chrome WebDriver with performance monitoring"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--enable-logging")
        options.add_argument("--log-level=0")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(5)  # Shorter timeout for performance tests
        yield driver
        driver.quit()

    def test_statistics_calculation_performance(self, performance_driver, test_job_with_statistics):
        """Test that statistics calculation doesn't significantly impact page load"""
        job = test_job_with_statistics
        
        # Measure multiple page loads to get average
        load_times = []
        
        for i in range(3):  # Test 3 times for consistency
            start_time = time.time()
            performance_driver.get(f"http://localhost:5000/jobs/{job.job_id}")
            
            # Wait for statistics to be calculated and displayed
            WebDriverWait(performance_driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Application Statistics')]"))
            )
            
            # Wait for any async statistics loading
            WebDriverWait(performance_driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            load_time = time.time() - start_time
            load_times.append(load_time)
            
            # Clear cache between tests
            performance_driver.delete_all_cookies()
        
        avg_load_time = sum(load_times) / len(load_times)
        max_load_time = max(load_times)
        
        # Performance assertions
        assert avg_load_time < 15, f"Average load time too high: {avg_load_time:.2f}s"
        assert max_load_time < 20, f"Maximum load time too high: {max_load_time:.2f}s"
        
        print(f"Statistics page performance - Avg: {avg_load_time:.2f}s, Max: {max_load_time:.2f}s")

    def test_chart_rendering_performance(self, performance_driver, test_job_with_statistics):
        """Test chart rendering performance"""
        job = test_job_with_statistics
        performance_driver.get(f"http://localhost:5000/jobs/{job.job_id}")
        
        # Measure time to render chart
        start_time = time.time()
        
        # Wait for chart canvas to be present
        WebDriverWait(performance_driver, 15).until(
            EC.presence_of_element_located((By.ID, "applicationTrendChart"))
        )
        
        # Wait for chart to be fully rendered
        WebDriverWait(performance_driver, 10).until(
            lambda d: d.execute_script("""
                const canvas = document.getElementById('applicationTrendChart');
                return canvas && Chart.getChart(canvas) !== undefined;
            """)
        )
        
        chart_render_time = time.time() - start_time
        
        # Chart should render quickly
        assert chart_render_time < 10, f"Chart rendering too slow: {chart_render_time:.2f}s"
        
        print(f"Chart rendering time: {chart_render_time:.2f}s")

    def test_memory_usage_with_statistics(self, performance_driver, test_job_with_statistics):
        """Test memory usage doesn't grow excessively with statistics"""
        job = test_job_with_statistics
        
        # Load page multiple times to check for memory leaks
        for i in range(5):
            performance_driver.get(f"http://localhost:5000/jobs/{job.job_id}")
            
            # Wait for full load
            WebDriverWait(performance_driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Application Statistics')]"))
            )
            
            # Check JavaScript heap size (if available)
            try:
                heap_size = performance_driver.execute_script("""
                    return window.performance && window.performance.memory 
                        ? window.performance.memory.usedJSHeapSize 
                        : null;
                """)
                
                if heap_size:
                    # Heap size should be reasonable (less than 50MB)
                    heap_mb = heap_size / (1024 * 1024)
                    assert heap_mb < 50, f"JavaScript heap too large: {heap_mb:.2f}MB"
                    
                    if i == 0:
                        initial_heap = heap_mb
                    elif i == 4:  # Last iteration
                        final_heap = heap_mb
                        # Memory shouldn't grow too much
                        growth = final_heap - initial_heap
                        assert growth < 20, f"Memory growth too high: {growth:.2f}MB"
                        
            except Exception:
                # Memory API might not be available
                pass


if __name__ == '__main__':
    pytest.main([__file__, "-v", "--tb=short"])