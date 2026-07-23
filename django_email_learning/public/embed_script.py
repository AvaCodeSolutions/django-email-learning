import json

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.views import View

from django_email_learning.public.api.views import embeddable_enrollment_enabled

# The token is stripped back out below - reversing with a real token isn't
# needed since we only want the fixed prefix in front of it.
_TOKEN_PLACEHOLDER = "TOKEN_PLACEHOLDER"

_EMBED_SCRIPT_TEMPLATE = r"""(function () {
  if (customElements.get('del-enroll-form') || customElements.get('del-newsletter-form')) {
    return;
  }

  var API_BASE = __API_BASE_JSON__;

  // Shared by both custom elements below.
  var BASE_WIDGET_STYLE =
    ':host { display:block; width:350px; max-width:100%; font-family: ui-sans-serif, system-ui, sans-serif; }' +
    'form { font-family: ui-sans-serif, system-ui, sans-serif; }' +
    '.field-group { display:flex; align-items:stretch; border:1px solid #d1d5db;' +
    ' border-radius:6px; overflow:hidden; }' +
    '.field-group input[type="email"] { flex:1; min-width:0; border:none;' +
    ' padding:10px 12px; font-size:14px; font-family:inherit; outline:none; }' +
    '.field-group button { flex-shrink:0; border:none; padding:10px 16px;' +
    ' font-size:14px; font-family:inherit; cursor:pointer; white-space:nowrap; }' +
    '.message { font-size:14px; margin-top:8px; }';

  // Only allow http(s) image URLs so a malicious course_image attribute can't
  // smuggle in a javascript:/data: URI.
  function safeImageUrl(value) {
    try {
      var url = new URL(value, window.location.href);
      return (url.protocol === 'http:' || url.protocol === 'https:') ? url.href : '';
    } catch (e) {
      return '';
    }
  }

  // Only allow simple CSS color values (hex, rg[b/a](), hsl[a](), or a plain
  // keyword) so button_bg_color/button_text_color can't break out of the
  // style attribute or inject extra declarations.
  function safeCssColor(value, fallback) {
    return /^(#[0-9a-fA-F]{3,8}|rgba?\([\d.,\s%]+\)|hsla?\([\d.,\s%]+\)|[a-zA-Z]+)$/.test(value)
      ? value
      : fallback;
  }

  class DelEnrollForm extends HTMLElement {
    connectedCallback() {
      var token = this.getAttribute('token') || '';
      var courseId = this.getAttribute('course_id') || '';
      var courseTitle = this.getAttribute('course_title') || '';
      var courseImage = safeImageUrl(this.getAttribute('course_image') || '');
      var showNewsletter = this.hasAttribute('news_letter_check');
      var newsletterTitle = this.getAttribute('newsletter_title') || '';
      var buttonBgColor = safeCssColor(this.getAttribute('button_bg_color') || '', '#4f46e5');
      var buttonTextColor = safeCssColor(this.getAttribute('button_text_color') || '', '#ffffff');
      var isPreview = this.hasAttribute('preview');

      var shadow = this.attachShadow({ mode: 'open' });

      // Build the DOM with createElement/textContent/setAttribute rather than
      // string-concatenated innerHTML. Every attribute here carries a
      // user-controllable value, and this keeps them as data (impossible to
      // break out of an attribute or inject markup/handlers).
      var style = document.createElement('style');
      style.textContent =
        BASE_WIDGET_STYLE +
        '.course-image { display:block; width:100%; max-height:180px; object-fit:cover;' +
        ' border-radius:6px; margin-bottom:10px; }' +
        '.course-title { font-size:16px; font-weight:600; margin:0 0 10px; }' +
        'label { display:flex; align-items:center; gap:6px; font-size:14px; margin-top:8px; }';
      shadow.appendChild(style);

      if (courseImage) {
        var image = document.createElement('img');
        image.className = 'course-image';
        image.setAttribute('src', courseImage);
        image.setAttribute('alt', '');
        shadow.appendChild(image);
      }

      if (courseTitle) {
        var title = document.createElement('h3');
        title.className = 'course-title';
        title.textContent = courseTitle;
        shadow.appendChild(title);
      }

      var form = document.createElement('form');

      var fieldGroup = document.createElement('div');
      fieldGroup.className = 'field-group';

      var emailInput = document.createElement('input');
      emailInput.type = 'email';
      emailInput.name = 'email';
      emailInput.placeholder = 'Your email address';
      emailInput.required = true;
      if (isPreview) {
        emailInput.readOnly = true;
        emailInput.tabIndex = -1;
      }
      fieldGroup.appendChild(emailInput);

      var submitButton = document.createElement('button');
      submitButton.type = 'submit';
      submitButton.textContent = 'Enroll';
      submitButton.disabled = isPreview;
      submitButton.style.background = buttonBgColor;
      submitButton.style.color = buttonTextColor;
      fieldGroup.appendChild(submitButton);

      form.appendChild(fieldGroup);

      if (showNewsletter) {
        var newsletterLabel = document.createElement('label');
        var newsletterCheckbox = document.createElement('input');
        newsletterCheckbox.type = 'checkbox';
        newsletterCheckbox.name = 'subscribe_to_newsletter';
        newsletterCheckbox.disabled = isPreview;
        newsletterLabel.appendChild(newsletterCheckbox);
        newsletterLabel.appendChild(document.createTextNode(' Subscribe to ' + newsletterTitle));
        form.appendChild(newsletterLabel);
      }

      var message = document.createElement('p');
      message.className = 'message';
      message.style.display = 'none';
      form.appendChild(message);

      shadow.appendChild(form);

      if (isPreview) {
        return;
      }

      form.addEventListener('submit', function (event) {
        event.preventDefault();
        message.style.display = 'none';
        fetch(API_BASE + token + '/enrollments/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: form.email.value,
            course_slug: courseId,
            subscribe_to_newsletter: form.subscribe_to_newsletter ? form.subscribe_to_newsletter.checked : false
          })
        })
          .then(function (response) {
            return response.json().then(function (data) { return { ok: response.ok, data: data }; });
          })
          .then(function (result) {
            message.style.display = 'block';
            if (result.ok && result.data.status === 'already_enrolled') {
              message.textContent = "You're already enrolled in this course.";
            } else if (result.ok) {
              message.textContent = "You're enrolled! Check your email to confirm.";
              form.reset();
            } else {
              message.textContent = (result.data && result.data.error) || 'Something went wrong. Please try again.';
            }
          })
          .catch(function () {
            message.style.display = 'block';
            message.textContent = 'Something went wrong. Please try again.';
          });
      });
    }
  }

  class DelNewsletterForm extends HTMLElement {
    connectedCallback() {
      var token = this.getAttribute('token') || '';
      var newsletterId = this.getAttribute('newsletter_id') || '';
      var buttonBgColor = safeCssColor(this.getAttribute('button_bg_color') || '', '#4f46e5');
      var buttonTextColor = safeCssColor(this.getAttribute('button_text_color') || '', '#ffffff');
      var isPreview = this.hasAttribute('preview');

      var shadow = this.attachShadow({ mode: 'open' });

      var style = document.createElement('style');
      style.textContent = BASE_WIDGET_STYLE;
      shadow.appendChild(style);

      var form = document.createElement('form');

      var fieldGroup = document.createElement('div');
      fieldGroup.className = 'field-group';

      var emailInput = document.createElement('input');
      emailInput.type = 'email';
      emailInput.name = 'email';
      emailInput.placeholder = 'Your email address';
      emailInput.required = true;
      if (isPreview) {
        emailInput.readOnly = true;
        emailInput.tabIndex = -1;
      }
      fieldGroup.appendChild(emailInput);

      var submitButton = document.createElement('button');
      submitButton.type = 'submit';
      submitButton.textContent = 'Subscribe';
      submitButton.disabled = isPreview;
      submitButton.style.background = buttonBgColor;
      submitButton.style.color = buttonTextColor;
      fieldGroup.appendChild(submitButton);

      form.appendChild(fieldGroup);

      var message = document.createElement('p');
      message.className = 'message';
      message.style.display = 'none';
      form.appendChild(message);

      shadow.appendChild(form);

      if (isPreview) {
        return;
      }

      form.addEventListener('submit', function (event) {
        event.preventDefault();
        message.style.display = 'none';
        fetch(API_BASE + token + '/newsletters/subscribe/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: form.email.value,
            newsletter_ids: [Number(newsletterId)]
          })
        })
          .then(function (response) {
            return response.json().then(function (data) { return { ok: response.ok, data: data }; });
          })
          .then(function (result) {
            message.style.display = 'block';
            if (result.ok) {
              message.textContent = "You've been subscribed! Check your email to confirm.";
              form.reset();
            } else {
              message.textContent = (result.data && result.data.error) || 'Something went wrong. Please try again.';
            }
          })
          .catch(function () {
            message.style.display = 'block';
            message.textContent = 'Something went wrong. Please try again.';
          });
      });
    }
  }

  customElements.define('del-enroll-form', DelEnrollForm);
  customElements.define('del-newsletter-form', DelNewsletterForm);
})();
"""


def embed_api_base_url() -> str:
    """The fixed URL prefix shared by every embed_enroll URL for this
    deployment (i.e. everything up to the token), e.g.
    'https://yourdomain.com/email-learning/api/public/embed/'. Computed via
    reverse() with a placeholder token so it stays correct regardless of the
    URL prefix a library user mounted django_email_learning.urls under.
    """
    placeholder_path = reverse(
        "django_email_learning:api_public:embed_enroll",
        kwargs={"token": _TOKEN_PLACEHOLDER},
    )
    base_path = placeholder_path.replace(f"{_TOKEN_PLACEHOLDER}/enrollments/", "")
    return f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{base_path}"


def build_embed_script_js() -> str:
    """The del-enroll-form and del-newsletter-form custom element
    definitions. Deliberately generic - contains no course/newsletter/
    organization/token data, only the deployment's fixed API base URL - so
    it's the same content for every widget placement, safe to cache
    aggressively.
    """
    return _EMBED_SCRIPT_TEMPLATE.replace("__API_BASE_JSON__", json.dumps(embed_api_base_url()))


class EmbedScriptView(View):
    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        if not embeddable_enrollment_enabled():
            return HttpResponse(status=404)
        response = HttpResponse(build_embed_script_js(), content_type="application/javascript")
        response["Cache-Control"] = "public, max-age=3600"
        return response
