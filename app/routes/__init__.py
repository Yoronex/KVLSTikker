from datetime import datetime

from dateutil import tz
from flask import flash, request, abort, make_response, render_template, jsonify, redirect, url_for

from app import round_up
from app.forms import *
from app.models import *


page_size = 100
pagination_range = 4


def get_usergroups_with_users():
    usergroups = Usergroup.query.all()
    for g in usergroups:
        if len(g.users.all()) == 0:
            usergroups.remove(g)
    return usergroups


def is_filled(data):
    if data is None:
        return False
    if data == '':
        return False
    if not data:
        return False
    return True


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.Config["ALLOWED_EXTENSIONS"]


def make_autopct(values):
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct * total / 100.0))
        return '{p:.2f}%  ({v:d})'.format(p=pct, v=val)

    return my_autopct


def convert_to_local_time(transactions):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    result = []

    for t in transactions:
        # utc = datetime.utcnow()
        utc = datetime.strptime(t.datetime, '%Y-%m-%d %H:%M:%S.%f')

        # Tell the datetime object that it's in UTC time zone since
        # datetime objects are 'naive' by default
        utc = utc.replace(tzinfo=from_zone)

        # Convert time zone
        result.append(utc.astimezone(to_zone))

    return result


def calculate_pagination_with_basequery(query, request_obj):
    # If no page id is provided...
    if request_obj.args.get('page') is None:
        # We set it to 1
        page = 1
    else:
        # Otherwise, we get it from the parameters and transform it into an integer
        page = int(request_obj.args.get('page'))
    # Get the total amount of rows for this table
    total_amount_of_entries = query.count()
    # Calculate the total amount of pages
    total_amount_of_pages = int(round_up(total_amount_of_entries / page_size, 0))
    # Calculate the offset in number of rows in a page
    offset_difference = total_amount_of_entries % page_size
    # Calculate the offset in number of pages
    offset = max(0, total_amount_of_pages - page)
    # Calculate the real offset in number of rows
    real_offset = offset * page_size - (page_size - offset_difference)
    # The offset cannot be negative, so if this is the case, we need to decrease the page size
    if real_offset < 0:
        real_page_size = page_size + real_offset
        real_offset = 0
    # If the offset is not negative, we simply copy the page size
    else:
        real_page_size = page_size
    # Create the data object that contains all necessary information
    pagination = {'pages': total_amount_of_pages,
                  'currentPage': page,
                  'minPage': max(1, int(page - pagination_range)),
                  'maxPage': min(total_amount_of_pages, page + pagination_range),
                  'offset': real_offset,
                  'pageSize': real_page_size,
                  'records': '{} ... {} van de {}'.format(page_size * (page - 1) + 1,
                                                          page_size * (page - 1) + real_page_size,
                                                          total_amount_of_entries),
                  }
    # Return this object
    return pagination


def flash_form_errors(errors):
    if len(errors.keys()) > 0:
        print(errors)
        for k, v in errors.items():
            for error in v:
                flash("Fout in formulier: {} - {}".format(k, error), "danger")


def apply_filters(query):
    if 'f_transaction_type' in request.args:
        t_type = request.args.get('f_transaction_type')
        if t_type == 'upgr':
            query = query.filter(Transaction.upgrade_id != None)
        elif t_type == 'pur':
            query = query.filter(Transaction.purchase_id != None)

    if 'f_transaction_user' in request.args and int(request.args.get('f_transaction_user')) > 0:
        query = query.filter(Transaction.user_id == int(request.args.get('f_transaction_user')))

    if 'f_transaction_product' in request.args and int(request.args.get('f_transaction_product')) > 0:
        query = query.filter(Transaction.purchase.has(product_id=int(request.args.get('f_transaction_product'))))

    if 'f_transaction_round' in request.args:
        t_round = request.args.get('f_transaction_round')
        if t_round == '1':
            query = query.filter(Transaction.purchase.has(round=True))
        elif t_round == '0':
            query = query.filter(Transaction.purchase.has(round=False))

    if 'f_user_usergroup' in request.args and int(request.args.get('f_user_usergroup')) > 0:
        query = query.filter(User.usergroup_id == int(request.args.get('f_user_usergroup')))
    if 'f_user_profitgroup' in request.args and int(request.args.get('f_user_profitgroup')) > 0:
        query = query.filter(User.profitgroup_id == int(request.args.get('f_user_profitgroup')))
    if 'f_user_deleted' in request.args:
        t_round = request.args.get('f_user_deleted')
        if t_round == '1':
            query = query.filter(User.deleted == True)
        elif t_round == '0':
            query = query.filter(User.deleted == False)

    if 'f_product_category' in request.args and request.args.get('f_product_category') != 'all':
        query = query.filter(Product.category == request.args.get('f_product_category'))
    if 'f_product_purchaseable' in request.args:
        t_round = request.args.get('f_product_purchaseable')
        if t_round == '1':
            query = query.filter(Product.purchaseable == True)
        elif t_round == '0':
            query = query.filter(Product.purchaseable == False)

    return query


def check_if_local_machine():
    if not app.config['VIEW_ONLY'] and request.remote_addr != "127.0.0.1":
        abort(403)


def check_if_not_view_only():
    if app.config['VIEW_ONLY']:
        abort(403)
