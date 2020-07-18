import click
from app import app, statshandler
from app.dbhandler import settings
from app.models import Transaction, Product, User
from datetime import datetime, timedelta


@app.cli.command("recalc-max")
def recalc_max():
    print('Recalculating all maximum daily stats values will overwrite the old values. This action is irreversible!')
    print('Are you sure you want to continue (y/n)?')
    answer = input()
    if answer != 'y':
        print('Aborted')
        return

    # First, reset the daily and the max stats
    statshandler.reset_max_stats()
    statshandler.reset_daily_stats(True)

    # Calculate the amount of days between the release of Tikker and today
    begin = datetime(year=2019, month=9, day=1, hour=12)
    now = datetime.now()
    days = (now - begin).days

    print("Recalculating... 0%", end="\r")

    # For every day...
    for i in range(0, days):
        # Get the purchase transactions of that day
        transactions = Transaction.query.filter(Transaction.timestamp > begin + timedelta(days=i),
                                                Transaction.timestamp < begin + timedelta(days=i + 1),
                                                Transaction.upgrade_id == None).all()
        # For each transaction...
        for t in transactions:
            # Get the purchase
            purchase = t.purchase
            # Update the daily stats with this purchase
            statshandler.update_daily_stats_purchase(purchase.user_id, purchase.product_id, purchase.amount,
                                                     purchase.round, purchase.price)
        # Reset the daily stats when this day is over, so we can continue with the next
        statshandler.reset_daily_stats(True)

        print("Recalculating... {}%".format(int(i / days * 45)), end="\r")

    # Loop again over all transactions, but now include every single one
    transactions = Transaction.query.all()
    for i in range(0, len(transactions)):
        # Apply the balance change, so we can find the maximum sum of all balances
        statshandler.update_daily_stats("euros", transactions[i].balchange)

        print("Recalculating... {}%".format(int(i / len(transactions) * 45) + 45), end="\r")

    # Finally, find the two maximum values of the amount of products and the amount of users
    # These two models however are not being tracked over time. Thus, the best thing we can do is to simply save their
    # current nummer at this point in time. The 'products' daily statistic can be tricked though: temporarily set some
    # old products to purchaseable and they will count.
    statshandler.update_daily_stats('products', Product.query.filter(Product.purchaseable == True,
                                                                     Product.id != settings['dinner_product_id'])
                                    .count())
    print("Recalculating... 95%", end="\r")
    statshandler.update_daily_stats('users', User.query.count())
    print("Recalculating... 100%")

    # We are done!
    return
