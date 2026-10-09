from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        raw = request.query_params.get(self.page_size_query_param)
        if raw is None:
            return self.page_size
        if len(raw) > 3 or not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= self.max_page_size:
            raise ValidationError({"page_size": ["Use an integer between 1 and 100."]})
        return int(raw)
