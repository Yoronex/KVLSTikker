import math

from flask import flash, abort, redirect

from app import dbhandler, socket
from app.models import Product


def purchase(cart, product_id):
    # Parse the raw cart string into something readable
    parsed_cart = parse_cart_string(cart)
    # Get the product object
    product = Product.query.get(product_id)
    # If borrel mode is enabled for this product...
    if dbhandler.borrel_mode_enabled and product_id in dbhandler.borrel_mode_drinks:
        # Create the purchases for everyone to make them count for the stats (with a price of 0)
        create_purchases(parsed_cart['orders'], product, parsed_cart['round'], 0)
        # Create an order for the paying user
        order = {'user_id': dbhandler.settings['borrel_mode_user'],
                 'amount': parsed_cart['total_bought']}
        # Let the paying user pay for everything
        success_messages = create_purchases([order], product, True, product.price)
    else:
        # Create purchases for every order
        success_messages = create_purchases(parsed_cart['orders'], product, parsed_cart['round'], product.price)

    # Create the final alert for both Tikker and Tikker BigScreen
    create_and_send_final_flash(success_messages)
    # Update the stats on BigScreen
    socket.update_stats()

    # If there are shared orders left...
    if parsed_cart['shared']:
        # Return this order
        return {'shared': True, 'shared_amount': parsed_cart['shared_amount']}
    else:
        return {'shared': False}


def purchase_together(cart, product_id, amount):
    # Parse the raw cart string into something readable
    parsed_cart = parse_cart_string(cart)
    # Get the product object
    product = Product.query.get(product_id)
    # If borrel mode is enabled for this product...
    if dbhandler.borrel_mode_enabled and product_id in dbhandler.borrel_mode_drinks:
        # Create the purchases for everyone to make them count for the stats (with a price of 0)
        create_purchases_shared(parsed_cart['orders'], product, parsed_cart['total_bought'],
                                parsed_cart['round'], 0, amount)
        # Create an order for the paying user
        order = {'user_id': dbhandler.settings['borrel_mode_user'],
                 'amount': parsed_cart['total_bought']}
        # Let the paying user pay for everything
        success_messages = create_purchases([order], product, True, product.price)
    else:
        # Create purchases for every order
        success_messages = create_purchases_shared(parsed_cart['orders'], product, parsed_cart['total_bought'],
                                                   parsed_cart['round'], product.price, amount)

    # Create the final alert for both Tikker and Tikker BigScreen
    create_and_send_final_flash(success_messages)
    # Update the stats on BigScreen
    socket.update_stats()


def purchase_dinner(cart, total_costs, comments):
    # Parse the raw cart string into something readable
    parsed_cart = parse_cart_string(cart)
    # Get the dinner ID
    dinner_id = dbhandler.settings['dinner_product_id']
    # If the dinner ID is None, return an error, as we should not have entered this method
    if dinner_id is None:
        raise ValueError("Dinner ID is None")
    # Get the product object
    product = Product.query.get(dinner_id)
    # Determine the price for one dinner
    price_pp = dbhandler.round_up(float(total_costs) / parsed_cart['total_bought'])
    # Add this to the inventory, so it can remain zero after purchasing
    dbhandler.add_inventory(dinner_id, parsed_cart['total_bought'], price_pp, comments)
    # Create the purchases for every order
    success_messages = create_purchases(parsed_cart['orders'], product, False, price_pp)

    # Create the final alert for both Tikker and Tikker BigScreen
    create_and_send_final_flash(success_messages)
    # Update the stats on BigScreen
    socket.update_stats()


def purchase_from_orders(orders, product_id, r=False):
    # Get the product object
    product = Product.query.get(product_id)
    # Because we only have orders and not a parsed cart, we have to calculate the total bought
    total_bought = sum(i['amount'] for i in orders)
    # If borrel mode is enabled for this product...
    if dbhandler.borrel_mode_enabled and product_id in dbhandler.borrel_mode_drinks:
        # Create the purchases for everyone to make them count for the stats (with a price of 0)
        create_purchases(orders, product, r, 0)
        # Create an order for the paying user
        order = {'user_id': dbhandler.settings['borrel_mode_user'],
                 'amount': total_bought}
        # Let the paying user pay for everything
        success_messages = create_purchases([order], product, True, product.price)
    else:
        # Create purchases for every order
        success_messages = create_purchases(orders, product, r, product.price)

    # Create the final alert for both Tikker and Tikker BigScreen
    create_and_send_final_flash(success_messages)
    # Update the stats on BigScreen
    socket.update_stats()


def parse_cart_string(cart):
    # resulting parsed object
    result = {'shared': False,
              'shared_amount': -1,
              'total_bought': 0}
    # Split the cart by the '&' sign
    split = cart.split('&')
    # If the resulting split has length 0, no cart is passed so we raise an error
    if len(split) == 0:
        abort(500)
    # If the first value is a 0, this cart is not a round, so we set the value accordingly
    if split[0] == "0":
        result['round'] = False
    else:
        result['round'] = True

    # Parsed list of orders
    orders = []
    # Loop over all split parts except the first one (which was the round boolean)
    for order in split[1:len(split)]:
        # Split by the second split value
        data = order.split('a')
        # If the user ID is a 0, it means some products will be shared, so we set the values accordingly
        if data[0] == '0':
            result['shared'] = True
            result['shared_amount'] = data[1]
        # Otherwise, it is an order made by a user
        else:
            result['total_bought'] += int(data[1])
            orders.append({'user_id': int(data[0]),
                           'amount': int(data[1])})
    # Put the orders list in the result object
    result['orders'] = orders
    # Return the result
    return result


def process_alert(alert, success_messages):
    if alert[3] == "success":
        q = alert[0]
        if math.floor(q) == q:
            q = math.floor(q)
        key = "{}x {} voor".format(q, alert[1])
        if key not in success_messages:
            success_messages[key] = alert[2]
        else:
            success_messages[key] = success_messages[key] + ", {}".format(alert[2])
    return success_messages


def create_and_send_final_flash(success_messages):
    final_flash = ""
    for front, end in success_messages.items():
        final_flash = final_flash + str(front) + " " + end + ", "
    if final_flash != "":
        socket.send_transaction(final_flash[:-2])
        flash(final_flash[:-2] + " verwerkt", "success")


def create_purchases(orders, product, r, price):
    success_messages = {}
    for o in orders:
        return_message = dbhandler.addpurchase(product.id, o['user_id'], o['amount'], r, price)
        process_alert(return_message, success_messages)
    return success_messages


def create_purchases_shared(orders, product, total_bought, r, price, initial_amount):
    success_messages = {}
    for o in orders:
        amount = dbhandler.round_up(o['amount'] * initial_amount / total_bought)
        return_message = dbhandler.addpurchase(product.id, o['user_id'], amount, r, price)
        process_alert(return_message, success_messages)
    return success_messages
