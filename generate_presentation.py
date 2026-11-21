import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml import parse_xml

def add_slide_transition(slide):
    """Add smooth push/fade transition to slide XML."""
    transition_xml = parse_xml(
        '<p:transition xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" spd="med">'
        '<p:fade/>'
        '</p:transition>'
    )
    slide._element.append(transition_xml)

def set_font(p, text, size=22, bold=False, color=RGBColor(30, 41, 59)):
    p.text = text
    p.font.name = "Times New Roman"
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.space_after = Pt(12)

def create_presentation(output_pptx):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Helper for adding standard slides
    def add_content_slide(title_text, bullet_lines, diagram_callback=None, image_path=None):
        slide = prs.slides.add_slide(blank_layout)
        add_slide_transition(slide)

        # Title Box
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.8))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        set_font(p, title_text, size=28, bold=True, color=RGBColor(15, 23, 42))

        # Text Box (Left side: width 6.2 inches)
        text_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(6.0), Inches(5.2))
        tf_body = text_box.text_frame
        tf_body.word_wrap = True

        for i, line in enumerate(bullet_lines):
            p_line = tf_body.paragraphs[0] if i == 0 else tf_body.add_paragraph()
            set_font(p_line, line, size=22, bold=False, color=RGBColor(30, 41, 59))

        # Right side: Diagram or Screenshot (x=7.2, y=1.5, w=5.3, h=5.2)
        if image_path and os.path.exists(image_path):
            slide.shapes.add_picture(image_path, Inches(7.2), Inches(1.6), width=Inches(5.3))
        elif diagram_callback:
            diagram_callback(slide, Inches(7.2), Inches(1.6), Inches(5.3), Inches(5.0))

        return slide

    # -------------------------------------------------------------
    # SLIDE 1: Title Slide
    # -------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    add_slide_transition(s1)

    t_box = s1.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(2.2))
    tf1 = t_box.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    set_font(p1, "Vision-Based Screen Layout Analysis and Visual Regression Testing Framework for CI/CD Pipelines", size=28, bold=True, color=RGBColor(15, 23, 42))

    sub_box = s1.shapes.add_textbox(Inches(1.0), Inches(4.2), Inches(11.333), Inches(2.5))
    tf_sub = sub_box.text_frame
    tf_sub.word_wrap = True
    lines = [
        "Academic Software Engineering Project Presentation",
        "Automated Pixel & DOM Regression Detection System",
        "Integrated with OpenCV, Selenium, Docker, and GitHub Actions",
        "Presenter: Vijay Bhaskar Reddy (Reg. No: 192425155)"
    ]
    for i, line in enumerate(lines):
        p_sub = tf_sub.paragraphs[0] if i == 0 else tf_sub.add_paragraph()
        p_sub.alignment = PP_ALIGN.CENTER
        set_font(p_sub, line, size=22, bold=False, color=RGBColor(51, 65, 85))

    # -------------------------------------------------------------
    # SLIDE 2: Abstract
    # -------------------------------------------------------------
    def draw_abstract_diagram(slide, x, y, w, h):
        # 3 Step Pipeline Blocks
        steps = [
            ("Screen Capture", "Automated Selenium Viewports"),
            ("Vision Processing", "OpenCV Absolute Pixel Diff & SSIM"),
            ("Quality Gate", "Pass/Fail CI/CD Decision")
        ]
        top = y + Inches(0.4)
        for title, desc in steps:
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(241, 245, 249)
            shape.line.color.rgb = RGBColor(37, 99, 235)
            shape.line.width = Pt(1.5)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            set_font(p, title, size=18, bold=True, color=RGBColor(15, 23, 42))
            p2 = tf.add_paragraph()
            p2.alignment = PP_ALIGN.CENTER
            set_font(p2, desc, size=14, bold=False, color=RGBColor(71, 85, 105))
            top += Inches(1.4)

    add_content_slide(
        "Abstract",
        [
            "• Modern web applications suffer from unintended visual breakage across CSS and component releases.",
            "• Traditional functional unit tests fail to detect cosmetic layout displacements and color shifts.",
            "• This framework combines computer vision with DOM geometry inspection to automate regression testing.",
            "• Provides automated pass/fail verification directly integrated into CI/CD build pipelines.",
            "• Produces mathematical diff percentages, bounding-box overlays, and false-color heatmaps."
        ],
        diagram_callback=draw_abstract_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 3: Literature Survey
    # -------------------------------------------------------------
    def draw_lit_diagram(slide, x, y, w, h):
        categories = [
            ("Traditional UI Testing", "Selenium/Cypress DOM assertions miss visual rendering bugs."),
            ("Commercial Cloud Tools", "Percy/Applitools require proprietary paid cloud infrastructure."),
            ("Proposed Solution", "Self-hosted, OpenCV pixel-accurate engine with zero licensing cost.")
        ]
        top = y + Inches(0.4)
        for cat, detail in categories:
            shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(248, 250, 252)
            shape.line.color.rgb = RGBColor(100, 116, 139)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, cat, size=18, bold=True, color=RGBColor(15, 23, 42))
            p2 = tf.add_paragraph()
            set_font(p2, detail, size=14, bold=False, color=RGBColor(51, 65, 85))
            top += Inches(1.4)

    add_content_slide(
        "Literature Survey",
        [
            "• DOM tree assertion tools cannot verify pixel colors, padding overlaps, or responsive breakage.",
            "• Manual visual verification is slow, labor-intensive, error-prone, and unsustainable for continuous releases.",
            "• Cloud-based SaaS testing suites introduce high licensing costs and data privacy constraints.",
            "• Structural Similarity Index (SSIM) provides superior perceptual fidelity compared to raw checksums.",
            "• A self-hosted vision pipeline provides complete governance and reproducibility within Docker."
        ],
        diagram_callback=draw_lit_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 4: Problem Statement
    # -------------------------------------------------------------
    def draw_problem_diagram(slide, x, y, w, h):
        problems = [
            ("Silent Visual Defects", "CSS changes displace elements without raising JS runtime exceptions."),
            ("Multi-Device Inconsistency", "Responsive viewports break across mobile, tablet, and desktop screens."),
            ("Pipeline Bottleneck", "Manual UI review delays CI/CD deployment cycles significantly.")
        ]
        top = y + Inches(0.4)
        for p_title, p_desc in problems:
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(254, 242, 242)
            shape.line.color.rgb = RGBColor(239, 68, 68)
            shape.line.width = Pt(1.5)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, p_title, size=18, bold=True, color=RGBColor(185, 28, 28))
            p2 = tf.add_paragraph()
            set_font(p2, p_desc, size=14, bold=False, color=RGBColor(71, 85, 105))
            top += Inches(1.4)

    add_content_slide(
        "Problem Statement",
        [
            "• Code updates frequently introduce subtle CSS regressions that pass functional unit testing suites.",
            "• Elements shift position, change brand colors, or disappear entirely without throwing runtime errors.",
            "• Cross-viewport responsive inconsistencies are difficult to detect manually across screen resolutions.",
            "• Lack of automated visual quality gates prevents true continuous deployment in enterprise pipelines.",
            "• Need for an automated system to capture, compare, and flag visual regressions deterministically."
        ],
        diagram_callback=draw_problem_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 5: Objectives and Proposed Solution
    # -------------------------------------------------------------
    def draw_objectives_diagram(slide, x, y, w, h):
        objs = [
            ("Objective 1: Precision", "OpenCV pixel difference and contour detection."),
            ("Objective 2: Automation", "Headless Selenium capture across 4 standard viewports."),
            ("Objective 3: CI/CD Quality Gate", "Automated exit-code reporting in GitHub Actions.")
        ]
        top = y + Inches(0.4)
        for title, desc in objs:
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(240, 253, 244)
            shape.line.color.rgb = RGBColor(34, 197, 94)
            shape.line.width = Pt(1.5)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, title, size=18, bold=True, color=RGBColor(21, 128, 61))
            p2 = tf.add_paragraph()
            set_font(p2, desc, size=14, bold=False, color=RGBColor(71, 85, 105))
            top += Inches(1.4)

    add_content_slide(
        "Objectives & Proposed Solution",
        [
            "• Build an automated headless screenshot capture engine supporting multiple responsive resolutions.",
            "• Develop computer vision algorithms using OpenCV for pixel difference and contour bounding boxes.",
            "• Implement DOM layout analysis to detect moved, resized, or missing structural components.",
            "• Create a professional web dashboard with SQLite persistence and strict baseline governance.",
            "• Provide seamless CI/CD quality gates via GitHub Actions, Docker, and multi-format reports."
        ],
        diagram_callback=draw_objectives_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 6: 3 Modules Overview
    # -------------------------------------------------------------
    def draw_three_modules(slide, x, y, w, h):
        mods = [
            ("Module 1: Capture Engine", "Headless Selenium, CDP Viewports & DOM Extraction"),
            ("Module 2: Vision & Layout Engine", "OpenCV Absolute Diff, SSIM, Contours & Jet Heatmaps"),
            ("Module 3: DevOps & Dashboard", "Flask Web UI, SQLite, Docker & GitHub Actions CI/CD")
        ]
        top = y + Inches(0.4)
        colors = [RGBColor(37, 99, 235), RGBColor(16, 185, 129), RGBColor(147, 51, 234)]
        for i, (m_title, m_desc) in enumerate(mods):
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(248, 250, 252)
            shape.line.color.rgb = colors[i]
            shape.line.width = Pt(2.0)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, m_title, size=18, bold=True, color=colors[i])
            p2 = tf.add_paragraph()
            set_font(p2, m_desc, size=14, bold=False, color=RGBColor(51, 65, 85))
            top += Inches(1.4)

    add_content_slide(
        "Project Architecture: 3 Core Modules",
        [
            "• The framework is engineered into three modular, high-cohesion subsystems.",
            "• Module 1 handles headless browser lifecycle, viewport scaling, and DOM hierarchy capture.",
            "• Module 2 executes mathematical computer vision difference analysis and heatmap generation.",
            "• Module 3 provides the management dashboard, database persistence, Docker, and CI/CD automation.",
            "• Clear separation of concerns enables high maintainability and independent unit testing."
        ],
        diagram_callback=draw_three_modules
    )

    # -------------------------------------------------------------
    # SLIDE 7: Module 1 Description
    # -------------------------------------------------------------
    def draw_m1_diagram(slide, x, y, w, h):
        steps = [
            ("WebDriver Initialization", "Chrome headless with emulation overrides."),
            ("Resolution Switching", "Desktop (1366x768), Laptop, Tablet, Mobile."),
            ("DOM Geometry Snapshot", "Bounding boxes, computed CSS, and IDs extracted.")
        ]
        top = y + Inches(0.4)
        for st, sd in steps:
            shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(239, 246, 255)
            shape.line.color.rgb = RGBColor(59, 130, 246)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, st, size=18, bold=True, color=RGBColor(30, 64, 175))
            p2 = tf.add_paragraph()
            set_font(p2, sd, size=14, bold=False, color=RGBColor(71, 85, 105))
            top += Inches(1.4)

    add_content_slide(
        "Module 1: Screenshot & DOM Capture Engine",
        [
            "• Controls Chrome and Chromium in headless mode across isolated container environments.",
            "• Employs Chrome DevTools Protocol (CDP) to guarantee exact device pixel dimensions.",
            "• Supports Desktop (1366x768), Laptop (1280x800), Tablet (768x1024), and Mobile (375x812).",
            "• Injects custom JavaScript to record DOM layout coordinates, computed styles, and visibility.",
            "• Stores raw baseline screenshots with structured naming and metadata in SQLite."
        ],
        diagram_callback=draw_m1_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 8: Module 1 Sample Screenshot (Baseline Screen)
    # -------------------------------------------------------------
    baseline_img = "C:/Users/vijay/Visual-Regression-Testing-Framework/report_assets/app_5_target_sample.png"
    add_content_slide(
        "Module 1: Baseline Screenshot Capture",
        [
            "• Represents the approved golden baseline screenshot captured by the Selenium engine.",
            "• Validates full page geometry and verifies that CSS renders without layout anomalies.",
            "• Captured at native 1366x768 desktop viewport with device scale factor equal to 1.",
            "• Saved in the baselines storage directory with strict read-only immutability.",
            "• Serves as the ground-truth standard for all subsequent automated regression comparisons."
        ],
        image_path=baseline_img
    )

    # -------------------------------------------------------------
    # SLIDE 9: Module 2 Description
    # -------------------------------------------------------------
    def draw_m2_diagram(slide, x, y, w, h):
        steps = [
            ("cv2.absdiff Processing", "Calculates absolute delta across color channels."),
            ("Binary Mask & Contours", "Filters noise and extracts defect bounding boxes."),
            ("cv2.COLORMAP_JET Heatmap", "Renders visual intensity and displacement density.")
        ]
        top = y + Inches(0.4)
        for st, sd in steps:
            shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(240, 253, 250)
            shape.line.color.rgb = RGBColor(20, 184, 166)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, st, size=18, bold=True, color=RGBColor(17, 94, 89))
            p2 = tf.add_paragraph()
            set_font(p2, sd, size=14, bold=False, color=RGBColor(71, 85, 105))
            top += Inches(1.4)

    add_content_slide(
        "Module 2: Computer Vision & Layout Engine",
        [
            "• Loads baseline and current screenshots into NumPy arrays with Unicode-safe path handlers.",
            "• Computes absolute pixel differences across RGB channels and applies grayscale thresholding.",
            "• Formulates difference percentage: Changed Pixels divided by Total Viewport Pixels times 100.",
            "• Identifies defect boundaries using OpenCV contour detection and renders red bounding boxes.",
            "• Synthesizes continuous Jet false-color heatmaps to visualize the intensity of UI shifts."
        ],
        diagram_callback=draw_m2_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 10: Module 2 Sample Screenshot (Difference Overlay & Heatmap)
    # -------------------------------------------------------------
    diff_box_img = "C:/Users/vijay/Visual-Regression-Testing-Framework/visual_regression/storage/diffs/diff_app1_20261113_194426.png"
    add_content_slide(
        "Module 2: Visual Difference & Heatmap Analysis",
        [
            "• Sample output generated after modifying the sample web application CSS styles.",
            "• Red bounding boxes accurately locate the altered CTA button, shifted headers, and missing signup button.",
            "• Jet colormap highlights high-density layout shifts in red and minor variances in cyan.",
            "• The comparison measured a 9.27% pixel change, exceeding the 0.5% threshold and triggering FAIL.",
            "• Provides human testers with immediate visual verification of exactly where the regression occurred."
        ],
        image_path=diff_box_img
    )

    # -------------------------------------------------------------
    # SLIDE 11: Module 3 Description & CI/CD Screenshot
    # -------------------------------------------------------------
    cicd_dag_img = "C:/Users/vijay/Visual-Regression-Testing-Framework/report_assets/github_2_workflow_dag_artifacts.jpg"
    add_content_slide(
        "Module 3: Web Dashboard, Docker & CI/CD",
        [
            "• Flask web dashboard featuring a dark navy sidebar, light background, and Chart.js metrics.",
            "• Comprehensive management of registered applications, viewports, and baseline approvals.",
            "• Multi-format report generator creating interactive HTML, JSON packets, and CSV summaries.",
            "• Dockerfile and Docker Compose bundle the dashboard and target application as microservices.",
            "• GitHub Actions pipeline executes the CLI runner and breaks builds automatically upon regression."
        ],
        image_path=cicd_dag_img
    )

    # -------------------------------------------------------------
    # SLIDE 12: Future Scope
    # -------------------------------------------------------------
    def draw_future_diagram(slide, x, y, w, h):
        items = [
            ("Cross-Browser Support", "Extending Selenium execution to Firefox and Safari/WebKit."),
            ("AI Semantic Grouping", "Classifying whether visual shifts represent intentional redesigns."),
            ("Cloud Storage Integrations", "Direct S3 and Google Cloud Storage artifact synchronisation.")
        ]
        top = y + Inches(0.4)
        for it, idesc in items:
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(250, 245, 255)
            shape.line.color.rgb = RGBColor(168, 85, 247)
            shape.line.width = Pt(1.5)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, it, size=18, bold=True, color=RGBColor(126, 34, 206))
            p2 = tf.add_paragraph()
            set_font(p2, idesc, size=14, bold=False, color=RGBColor(71, 85, 105))
            top += Inches(1.4)

    add_content_slide(
        "Future Scope",
        [
            "• Expand browser testing grid to support native Firefox, Safari (WebKit), and Microsoft Edge.",
            "• Implement smart visual component recognition to isolate font rendering anti-aliasing variations.",
            "• Add dynamic video recording of page rendering workflows during visual regression runs.",
            "• Support Slack, Microsoft Teams, and email webhook notifications for instant build failure alerts.",
            "• Introduce automated baseline auto-tagging based on semantic Git release versioning."
        ],
        diagram_callback=draw_future_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 13: Conclusion
    # -------------------------------------------------------------
    def draw_conclusion_diagram(slide, x, y, w, h):
        points = [
            ("100% Deterministic", "OpenCV pixel-level precision eliminates testing guesswork."),
            ("Full CI/CD Integration", "GitHub Actions quality gates prevent broken UI releases."),
            ("Zero Cloud Cost", "Self-hosted Docker architecture avoids expensive commercial SaaS fees.")
        ]
        top = y + Inches(0.4)
        for pt, pd in points:
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top, w, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor(240, 253, 244)
            shape.line.color.rgb = RGBColor(34, 197, 94)
            shape.line.width = Pt(1.5)
            tf = shape.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            set_font(p, pt, size=18, bold=True, color=RGBColor(21, 128, 61))
            p2 = tf.add_paragraph()
            set_font(p2, pd, size=14, bold=False, color=RGBColor(71, 85, 105))
            top += Inches(1.4)

    add_content_slide(
        "Conclusion",
        [
            "• Successfully developed an end-to-end vision-based visual regression testing framework.",
            "• Solved the limitation of traditional DOM assertions by validating exact rendered pixel geometry.",
            "• Demonstrated accurate detection of color alterations, element shifts, and missing UI components.",
            "• Validated containerized execution with Docker Compose and automated GitHub Actions workflows.",
            "• Delivers a reliable, production-ready quality gate for modern software engineering CI/CD pipelines."
        ],
        diagram_callback=draw_conclusion_diagram
    )

    # -------------------------------------------------------------
    # SLIDE 14: Thank You
    # -------------------------------------------------------------
    s14 = prs.slides.add_slide(blank_layout)
    add_slide_transition(s14)

    ty_box = s14.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.333), Inches(1.5))
    tf14 = ty_box.text_frame
    p14 = tf14.paragraphs[0]
    p14.alignment = PP_ALIGN.CENTER
    set_font(p14, "Thank You", size=28, bold=True, color=RGBColor(15, 23, 42))

    info_box = s14.shapes.add_textbox(Inches(1.0), Inches(3.8), Inches(11.333), Inches(2.5))
    tf_info = info_box.text_frame
    lines14 = [
        "Questions & Discussion",
        "Project: Visual Regression Testing Framework for CI/CD Pipelines",
        "Repository: github.com/192425155KVijayBhsakarReddy/Visual-Regression-Testing-Framework",
        "Candidate: Vijay Bhaskar Reddy (192425155)"
    ]
    for i, line in enumerate(lines14):
        p_info = tf_info.paragraphs[0] if i == 0 else tf_info.add_paragraph()
        p_info.alignment = PP_ALIGN.CENTER
        set_font(p_info, line, size=22, bold=False, color=RGBColor(71, 85, 105))

    prs.save(output_pptx)
    print(f"Presentation generated successfully at: {output_pptx}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "Visual_Regression_Testing_Presentation.pptx"
    create_presentation(out_file)

