from datetime import datetime


def year(request):
    now_year = datetime.now().year
    return {
        'year': now_year,
    }
