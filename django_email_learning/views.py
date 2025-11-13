from django.views.generic import TemplateView


class ConsoleHomeView(TemplateView):
    template_name = "console_home.html"
