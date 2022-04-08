from django.core.paginator import Paginator
from yatube.settings import NUM_OF_POSTS_ON_PAGE


def paginate(posts, request):
    paginator = Paginator(posts, NUM_OF_POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
