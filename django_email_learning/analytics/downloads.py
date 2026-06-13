import csv
from django.http import HttpResponse
from django.db.models import QuerySet


def csv_response(
    filename: str, headers: list[str], rows: QuerySet | list
) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response
