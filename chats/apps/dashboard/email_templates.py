def get_report_ready_email(project_name: str, download_url: str):
    """
    Returns (plain_text, html) for report ready email.

    Args:
        project_name: Name of the project
        download_url: URL to download the report

    Returns:
        Tuple of (plain_text_body, html_body)
    """
    plain_text = f"""The custom report for the project {project_name} is ready.

Copy and paste the URL below to download the report:

{download_url}

This link will expire in 7 days."""

    html = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2>Custom Report Ready</h2>
    <p>The custom report for the project <strong>{project_name}</strong> is ready.</p>
    <p style="font-size: 14px; color: #666; margin: 20px 0;">
        Click the link below to download the report:
    </p>
    <p style="background: #f4f4f4; padding: 15px; border-left: 4px solid #4CAF50;
              word-wrap: break-word; font-family: monospace; font-size: 12px; margin: 20px 0;">
        {download_url}
    </p>
    <p style="font-size: 12px; color: #999;">
        This link will expire in 7 days.
    </p>
</body>
</html>"""

    return plain_text, html
