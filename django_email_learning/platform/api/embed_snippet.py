import json

from django.utils.html import escape


def build_embed_snippet(*, embed_enroll_url: str, course_slug: str, newsletter_title: str | None) -> str:
    """Builds a self-contained HTML/JS snippet an organization can paste onto
    their own site to enroll learners via the embed API (EMBEDDABLE_ENROLLMENT_ENABLED).

    Values landing in HTML text (newsletter_title) go through Django's escape()
    so they're safe as markup; values landing inside the <script> block
    (embed_enroll_url, course_slug) go through json.dumps() so they're safe as
    JS string literals - these are two different escaping contexts and neither
    filter is safe for the other one.
    """
    checkbox_html = ""
    if newsletter_title:
        label = escape(f"Subscribe to {newsletter_title}")
        checkbox_html = f"""
      <label style="display:flex;align-items:center;gap:6px;font-size:14px;margin-top:8px;">
        <input type="checkbox" name="subscribe_to_newsletter" />
        {label}
      </label>"""

    return f"""<div>
  <form>
    <input type="email" name="email" placeholder="Your email address" required
      style="display:block;width:100%;padding:8px;box-sizing:border-box;font-size:14px;" />{checkbox_html}
    <button type="submit" style="margin-top:8px;padding:8px 16px;font-size:14px;">Enroll</button>
    <p class="embed-message" style="display:none;font-size:14px;"></p>
  </form>
  <script>
    (function () {{
      var container = document.currentScript.closest('div');
      var form = container.querySelector('form');
      var message = container.querySelector('.embed-message');
      form.addEventListener('submit', function (event) {{
        event.preventDefault();
        message.style.display = 'none';
        fetch({json.dumps(embed_enroll_url)}, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            email: form.email.value,
            course_slug: {json.dumps(course_slug)},
            subscribe_to_newsletter: form.subscribe_to_newsletter ? form.subscribe_to_newsletter.checked : false
          }})
        }})
          .then(function (response) {{
            return response.json().then(function (data) {{ return {{ ok: response.ok, data: data }}; }});
          }})
          .then(function (result) {{
            message.style.display = 'block';
            if (result.ok && result.data.status === 'already_enrolled') {{
              message.textContent = "You're already enrolled in this course.";
            }} else if (result.ok) {{
              message.textContent = "You're enrolled! Check your email to confirm.";
              form.reset();
            }} else {{
              message.textContent = (result.data && result.data.error) || 'Something went wrong. Please try again.';
            }}
          }})
          .catch(function () {{
            message.style.display = 'block';
            message.textContent = 'Something went wrong. Please try again.';
          }});
      }});
    }})();
  </script>
</div>"""
