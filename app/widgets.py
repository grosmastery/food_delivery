from django.forms import FileInput


class ImageWidget(FileInput):
    template_name = 'widgets/file.html'
