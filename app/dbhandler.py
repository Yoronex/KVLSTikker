from app import app, db, stats
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction, Inventory, Recipe, Inventory_usage, Setting, Quote
from werkzeug.utils import secure_filename
from datetime import datetime
from random import randrange
import os
from sqlalchemy import and_


settings = {}


def initialize_settings():
    global settings
    default_settings = {'dinner_product_id': None}
    sses = Setting.query.all()
    settings_keys = []
    for s in sses:
        settings_keys.append(s.key)

    for k in default_settings.keys():
        if k not in settings_keys:
            s = Setting(key=k)
            db.session.add(s)
            db.session.commit()

    for s in Setting.query.all():
        settings[s.key] = s.value


initialize_settings()


def remove_existing_file(filename):
    file_loc = os.path.join(app.config["UPLOAD_FOLDER"] + filename)
    if os.path.exists(file_loc):
        os.remove(file_loc)


def create_filename(product, old_filename, image, character):
    filename, file_extension = os.path.splitext(secure_filename(image.filename))
    filename = str(product.id) + character + "-" + str(int(old_filename.split('-')[1]) + 1) + file_extension
    remove_existing_file(filename)
    return filename


def addpurchase(drink_id, user_id, quantity, rondje):
    if type(quantity) is float:
        quantity = float(round(quantity * 100)) / 100
    drink = Product.query.get(drink_id)
    user = User.query.get(user_id)

    if drink.recipe_input is None:
        inventory = take_from_inventory(user, drink_id, quantity)
    else:
        inventory = {'costs': 0, 'inventory_usage': []}
        # added_price = 0
        # for key, val in drink.recipe_input.items():
        for r in Recipe.query.filter(Recipe.product_id == drink.id).all():
            result = take_from_inventory(user, r.ingredient_id, r.quantity * quantity)
            inventory['costs'] = inventory['costs'] + result['costs']
            inventory['inventory_usage'] = inventory['inventory_usage'] + result['inventory_usage']
    profitgroup = Usergroup.query.get(user.profitgroup_id)
    profit = drink.price * quantity - inventory['costs']
    profitgroup.profit = profitgroup.profit + profit
    db.session.commit()

    user.balance = user.balance - float(drink.price) * quantity
    purchase = Purchase(user_id=user.id, timestamp=datetime.now(), product_id=drink.id, price=drink.price,
                        amount=quantity, round=rondje)
    db.session.add(purchase)
    db.session.commit()

    for x in inventory['inventory_usage']:
        i_u = Inventory_usage(purchase_id=purchase.id, inventory_id=x['id'], quantity=x['quantity'])
        db.session.add(i_u)
        db.session.commit()
        i_u = None

    balchange = -drink.price * quantity
    transaction = Transaction(user_id=user.id, timestamp=datetime.now(), purchase_id=purchase.id,
                              balchange=balchange, newbal=user.balance)
    db.session.add(transaction)
    db.session.commit()

    stats.update_daily_stats_product(drink_id, quantity)
    stats.update_daily_stats('euros', balchange)
    stats.update_daily_stats('purchases', 1)
    if rondje:
        stats.update_daily_stats('rounds', 1)

    # return "{}x {} voor {} verwerkt".format(quantity, drink.name, user.name), "success"
    return quantity, drink.name, user.name, "success"


def addbalance(user_id, description, amount):
    upgrade = Upgrade(user_id=user_id, description=description, timestamp=datetime.now(), amount=amount)
    db.session.add(upgrade)
    db.session.commit()
    user = User.query.get(upgrade.user_id)
    user.balance = user.balance + float(amount)
    transaction = Transaction(user_id=user_id, timestamp=datetime.now(), upgrade_id=upgrade.id,
                              balchange=upgrade.amount,
                              newbal=user.balance)
    db.session.add(transaction)
    db.session.commit()

    stats.update_daily_stats('euros', upgrade.amount)

    return "Gebruiker {} heeft succesvol opgewaardeerd met €{}".format(user.name,
                                                                       str("%.2f" % upgrade.amount).replace(".",
                                                                                                            ",")), "success"


def parse_recipe(recipe):
    if recipe != "":
        components = recipe.split(",")
        result_recipe = {}
        for c in components:
            data = c.replace(" ", "").split("x")
            if int(data[0]) <= 0 or int(data[1]) <= 0 or len(data) != 2:
                return "Recept voldoet niet aan de gegeven syntax!", "danger"
            len_a = int(len(data[0])) + int(len(data[1])) + 1
            len_b = int(len(c.replace(" ", "")))
            if len_a != len_b:
                return "Recept voldoet niet aan de gegeven syntax!", "danger"
            data[0] = int(data[0])
            data[1] = int(data[1])
            if Product.query.get(data[1]) is None or Product.query.get(data[1]).purchaseable is False:
                return "Product met ID {} bestaat niet of is niet beschikbaar!".format(str(data[1])), "danger"
            if Recipe.query.filter(Recipe.product_id == data[1]).count() > 0:
                return "Ingrediënt met ID {} bestaat zelf ook uit ingredienten!".format(str(data[1])), "danger"
            result_recipe[data[1]] = data[0]
        if len(result_recipe) <= 1:
            return "Een recept kan niet uit één type product bestaan!"
        return result_recipe
    return None


def adddrink(name, price, order, image, hoverimage, recipe, inventory_warning, alcohol, volume, unit):
    result_recipe = parse_recipe(recipe)
    if type(result_recipe) is tuple:
        return result_recipe
    if inventory_warning is None:
        inventory_warning = 0
    s_filename, s_file_extension = os.path.splitext(secure_filename(image.filename))
    if s_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
        return "Statische afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"
    if hoverimage != "":
        h_filename, h_file_extension = os.path.splitext(secure_filename(hoverimage.filename))
        if h_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
            return "Hover afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"

    amount_of_prod = Product.query.count()
    if order < amount_of_prod:
        p_ord = Product.query.filter(Product.order >= order).all()
        for i in range(0, len(p_ord)):
            p_ord[i].order = p_ord[i].order + 1
    elif order >= amount_of_prod:
        order = amount_of_prod + 1

    if result_recipe is not None:
        product = Product(name=name, price=price, order=order, purchaseable=True, image="", hoverimage="",
                          recipe_input=result_recipe)
    else:
        if volume is "":
            volume = "0"
        if alcohol is "":
            alcohol = "0"
        product = Product(name=name, price=price, order=order, purchaseable=True, image="", hoverimage="",
                          inventory_warning=inventory_warning, volume=int(float(volume)), unit=unit,
                          alcohol=float(alcohol.replace(",", ".").replace("%", "").replace(" ", "")) / 100)
    db.session.add(product)
    db.session.commit()

    if result_recipe is not None:
        for key, val in result_recipe.items():
            db.session.add(Recipe(product_id=product.id, ingredient_id=key, quantity=val))
        db.session.commit()

    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    product.image = create_filename(product, str(product.id) + "s-0", image, "s")
    image.save(os.path.join(app.config["UPLOAD_FOLDER"], product.image))

    if hoverimage == "":
        product.hoverimage = product.image
    else:
        product.hoverimage = create_filename(product, str(product.id) + "h-0", hoverimage, "h")
        hoverimage.save(os.path.join(app.config["UPLOAD_FOLDER"], product.hoverimage))
    db.session.commit()

    stats.update_daily_stats('products', 1)

    return "Product {} succesvol aangemaakt".format(product.name), "success"


def adduser(name, email, group, profitgroup, birthday):
    user = User(name=name, email=email, usergroup_id=group, profitgroup_id=profitgroup, birthday=birthday)
    db.session.add(user)
    db.session.commit()

    stats.update_daily_stats('users', 1)

    return "Gebruiker {} succesvol geregistreerd".format(user.name), "success"


def addusergroup(name):
    usergroup = Usergroup(name=name, )
    db.session.add(usergroup)
    db.session.commit()
    return "Groep {} succesvol aangemaakt".format(usergroup.name), "success"


def addquote(q):
    quote = Quote(timestamp=datetime.now(), value=q)
    db.session.add(quote)
    db.session.commit()


def deluser(user_id):
    user = User.query.get(user_id)
    name = user.name
    for t in user.transactions.all():
        db.session.delete(t)
    for u in user.upgrades.all():
        db.session.delete(u)
    negative_inventory_found = False
    for p in user.purchases.all():
        for i in Inventory_usage.query.filter(Inventory_usage.purchase_id == p.id).all():
            if i.amount < 0:
                negative_inventory_found = True
        db.session.delete(p)

    if negative_inventory_found:
        db.session.rollback()
        return "Verwijderen van gebruiker {} mislukt: er staat nog negatieve inventaris op zijn naam!".format(
            name), "danger"
    else:
        db.session.delete(user)
        db.session.commit()

        stats.update_daily_stats('users', -1)

        return "Gebruiker {} verwijderd".format(name), "success"


def deltransaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    user = User.query.get(transaction.user_id)
    profitgroup = Usergroup.query.get(user.profitgroup_id)

    if transaction.purchase_id is None:
        upgrade = Upgrade.query.get(transaction.upgrade_id)
        db.session.delete(upgrade)
    else:
        purchase = Purchase.query.get(transaction.purchase_id)
        profitgroup.profit = profitgroup.profit - purchase.price * purchase.amount
        inv_usage = Inventory_usage.query.filter(Inventory_usage.purchase_id == purchase.id).all()
        if type(inv_usage) is not list:
            inv_usage = [inv_usage]
        for i in range(0, len(inv_usage)):
            inventory = Inventory.query.get(inv_usage[i].inventory_id)
            inventory.quantity = inventory.quantity + inv_usage[i].quantity
            profitgroup.profit = profitgroup.profit + inventory.price_before_profit * inv_usage[i].quantity
            db.session.delete(inv_usage[i])
            db.session.commit()
            inventory = None

        # inventory_usage = purchase.inventory
        # print(str(inventory_usage))
        # for i in inventory_usage:
        #    inv = Inventory.query.get(i['id'])
        #    inv.quantity = inv.quantity + i['quantity']
        #    profitgroup.profit = profitgroup.profit + inv.price_before_profit * i['quantity']
        #    db.session.commit()
        #    inv = None

        recipe = Recipe.query.filter(Recipe.product_id == purchase.product_id).all()
        if len(recipe) == 0:
            fix_negative_inventory(purchase.product_id)
        else:
            for r in recipe:
                fix_negative_inventory(r.ingredient_id)
        db.session.delete(purchase)

    for t in Transaction.query.filter(Transaction.user_id == transaction.user_id,
                                      Transaction.timestamp > transaction.timestamp).all():
        t.newbal = t.newbal - transaction.balchange
    user.balance = user.balance - transaction.balchange
    db.session.delete(transaction)
    db.session.commit()
    return "Transactie met ID {} succesvol verwijderd!".format(transaction.id), "success"


def deldrink(drink_id):
    product = Product.query.get(drink_id)
    product.purchaseable = False
    db.session.commit()
    return 'Product {} is niet meer beschikbaar'.format(product.name), "success"


def delusergroup(usergroup_id):
    usergroup = Usergroup.query.get(usergroup_id)
    db.session.delete(usergroup)
    db.session.commit()
    return "Groep {} verwijderd".format(usergroup.name), "success"


def editdrink_attr(product_id, name, price, order, purchaseable, recipe, inventory_warning, alcohol, volume, unit):
    result_recipe = parse_recipe(recipe)
    if type(result_recipe) is tuple:
        return result_recipe

    product = Product.query.get(product_id)

    if product.recipe_input != result_recipe:
        for r in Recipe.query.filter(Recipe.product_id == product.id):
            db.session.delete(r)
        for key, val in result_recipe:
            db.session.add(Recipe(product_id=product.id, ingredient_id=key, quantity=val))

    purchaseable_old = product.purchaseable

    product.name = name
    product.price = price
    if order > Product.query.count():
        order = Product.query.count()
    if order < product.order:
        p_ord = Product.query.filter(Product.order >= order, Product.order < product.order).all()
        for i in range(0, len(p_ord)):
            p_ord[i].order = p_ord[i].order + 1
    elif order > product.order:
        p_ord = Product.query.filter(Product.order <= order, Product.order > product.order).all()
        for i in range(0, len(p_ord)):
            p_ord[i].order = p_ord[i].order - 1
    product.order = order
    product.purchaseable = purchaseable
    product.recipe_input = result_recipe
    product.inventory_warning = inventory_warning
    if alcohol != "":
        product.alcohol = float(str(alcohol).replace(",", ".").replace("%", "").replace(" ", "")) / 100
    else:
        product.alcohol = None
    product.volume = int(float(volume))
    product.unit = unit
    db.session.commit()

    if purchaseable_old is True and purchaseable is False:
        stats.update_daily_stats('products', -1)
    elif purchaseable_old is False and purchaseable is True:
        stats.update_daily_stats('products', 1)

    return "Product {} (ID: {}) succesvol aangepast!".format(product.name, product.id), "success"


def editdrink_price(product_id, price):
    product = Product.query.get(product_id)
    product.price = price
    db.session.commit()


def editdrink_image(product_id, image, hoverimage):
    product = Product.query.get(product_id)
    if image != "":
        s_filename, s_file_extension = os.path.splitext(secure_filename(image.filename))
        if s_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
            return "Statische afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"
        product.image = create_filename(product, os.path.splitext(product.image)[0], image, "s")
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], product.image))
    if hoverimage != "":
        h_filename, h_file_extension = os.path.splitext(secure_filename(hoverimage.filename))
        if h_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
            return "Hover afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"
        product.hoverimage = create_filename(product, os.path.splitext(product.image)[0], hoverimage, "h")
        hoverimage.save(os.path.join(app.config["UPLOAD_FOLDER"], product.hoverimage))
    db.session.commit()
    return "Afbeelding van product {} (ID: {}) succesvol aangepast!".format(product.name, product.id), "success"


# -- Inventory management -- #

def get_inventory_stock(product_id):
    if Product.query.get(product_id).recipe_input is None:
        return [get_inventory_stock_for_product(product_id)]
    else:
        result = []
        for key, value in Product.query.get(product_id).recipe_input.items():
            p = Product.query.get(key)
            stock = get_inventory_stock_for_product(key)
            stock["name"] = p.name
            stock["recipe_quantity"] = value
            result.append(stock)
        return result


def get_inventory_stock_for_product(product_id):
    result = {}
    inventories = Inventory.query.filter(Inventory.product_id == product_id).all()
    result['inventory_warning'] = Product.query.get(product_id).inventory_warning
    if len(inventories) == 0:
        result['quantity'] = 0
        result['entries'] = 0
        result['oldest'] = None
        result['newest'] = None
    else:
        result['quantity'] = 0
        result['entries'] = len(inventories)
        result['oldest'] = inventories[0].timestamp
        result['newest'] = inventories[-1].timestamp
        for i in inventories:
            result['quantity'] = result['quantity'] + int(i.quantity)
        if result['quantity'] < 0:
            result['oldest'] = None
            result['newest'] = None
    return result


def get_product_stats(product_id):
    result = {}

    if Recipe.query.filter(Recipe.product_id == product_id).count() == 0:
        p = Product.query.get(product_id)
        result['alcohol'] = p.volume * p.alcohol
        result['volume'] = p.volume / 1000
        result['stock'] = [
            {"product": p.name, "quantity": get_inventory(p.id), "inventory_warning": p.inventory_warning}]
    else:
        result['alcohol'] = 0
        result['stock'] = []
        result['volume'] = 0.0
        for r in Recipe.query.filter(Recipe.product_id == product_id).all():
            p = Product.query.get(r.ingredient_id)
            result['alcohol'] = result['alcohol'] + p.volume * p.alcohol
            result['stock'].append(
                {"product": p.name, "quantity": get_inventory(p.id), "inventory_warning": p.inventory_warning})
            result['volume'] = result['volume'] + p.volume / 1000

    purchases = Purchase.query.filter(Purchase.product_id == product_id).all()
    users = {u.id: [0, 0] for u in User.query.all()}
    result['total_bought'] = 0
    for pur in purchases:
        result['total_bought'] = result['total_bought'] + pur.amount
        if not pur.round:
            users[pur.user_id][0] = users[pur.user_id][0] + pur.amount
        else:
            users[pur.user_id][1] = users[pur.user_id][1] + 1
    largest_consumer = None
    largest_round_giver = None
    largest_consumer_amount = 0
    largest_round_giver_amount = 0
    for user, amount in users.items():
        if amount[0] > largest_consumer_amount:
            largest_consumer = user
            largest_consumer_amount = amount[0]
        if amount[1] > largest_round_giver_amount:
            largest_round_giver = user
            largest_round_giver_amount = amount[1]

    result['largest_consumer'] = {'user': largest_consumer, 'amount': largest_consumer_amount}
    result['largest_rounder'] = {'user': largest_round_giver, 'amount': largest_round_giver_amount}
    return result


def find_inventory(product_id, index):
    inventories = Inventory.query.filter(Inventory.product_id == product_id, Inventory.quantity != 0).all()
    if len(inventories) == 0:
        return None
    elif type(inventories) is Inventory:
        return inventories
    else:
        return inventories[index]


def find_newest_inventory(product_id):
    return find_inventory(product_id, -1)


def find_oldest_inventory(product_id):
    return find_inventory(product_id, 0)


def get_inventory(product_id):
    inventories = Inventory.query.filter(and_(Inventory.product_id == product_id, Inventory.quantity != 0)).all()
    sum = 0
    for i in inventories:
        sum = sum + i.quantity
    return sum


def add_inventory(p_id, quantity, price_before_profit, note):
    old_inv = find_oldest_inventory(p_id)
    neg_inv = Inventory.query.filter(Inventory.product_id == p_id, Inventory.quantity < 0).all()
    new_inv = Inventory(product_id=p_id, timestamp=datetime.now(), quantity=float(quantity),
                        price_before_profit=price_before_profit, note=note)
    db.session.add(new_inv)
    db.session.commit()
    for n in neg_inv:
        fix_neg_inv(n, new_inv)
        if new_inv.quantity == 0:
            break

    product = Product.query.get(p_id)
    return "{} {} toegevoegd aan inventaris!".format(str(quantity), product.name), "success"


def fix_neg_inv(old_inv, new_inv):
    inv_use = Inventory_usage.query.filter(Inventory_usage.inventory_id == old_inv.id).all()
    for i in range(0, len(inv_use)):
        if new_inv.quantity == 0:
            break
        pur = Purchase.query.get(inv_use[i].purchase_id)
        if pur is not None:
            user = User.query.get(pur.user_id)
            if user is not None:
                profitgroup = Usergroup.query.get(user.profitgroup_id)
        else:
            profitgroup = None

        if inv_use[i].quantity > new_inv.quantity:
            new_inv_use = Inventory_usage(purchase_id=inv_use[i].purchase_id, inventory_id=new_inv.id,
                                          quantity=new_inv.quantity)
            db.session.add(new_inv_use)
            inv_use[i].quantity = inv_use[i].quantity - new_inv.quantity
            if profitgroup is not None:
                profitgroup.profit = profitgroup.profit - (new_inv.price_before_profit * new_inv_use.quantity)
            new_inv.quantity = 0
            old_inv.quantity = old_inv.quantity + new_inv_use.quantity
            db.session.commit()
            break
        else:
            inv_use[i].inventory_id = new_inv.id
            if profitgroup is not None:
                profitgroup.profit = profitgroup.profit - (new_inv.price_before_profit * inv_use[i].quantity)
            new_inv.quantity = new_inv.quantity - inv_use[i].quantity
            old_inv.quantity = old_inv.quantity + inv_use[i].quantity
            db.session.commit()


def take_from_inventory(user, product_id, quantity):
    product = Product.query.get(product_id)
    if user is not None:
        profitgroup = Usergroup.query.get(user.profitgroup_id)
    else:
        profitgroup = None
    added_costs = 0
    inventory_usage = []
    while quantity > 0:
        inventory = find_oldest_inventory(product_id)
        if inventory is None:
            inventory = Inventory(product_id=product_id, timestamp=datetime.utcnow(), quantity=float(- quantity),
                                  price_before_profit=0.0, note="Noodinventaris")
            db.session.add(inventory)
            db.session.commit()
            inventory_usage.append({"id": inventory.id, "quantity": quantity})
            db.session.commit()
            break
        else:
            if quantity < inventory.quantity:
                # profit = product.price - inventory.price_before_profit
                if profitgroup is not None:
                    # profitgroup.profit = profitgroup.profit + (inventory.price_before_profit * quantity)
                    added_costs = added_costs + (inventory.price_before_profit * quantity)
                inventory_usage.append({"id": inventory.id, "quantity": quantity})
                inventory.quantity = inventory.quantity - quantity
                break
            elif quantity >= inventory.quantity > 0.0:
                # profit = product.price - inventory.price_before_profit  # calculate profit
                if profitgroup is not None:
                    # profitgroup.profit = profitgroup.profit + (inventory.price_before_profit * inventory.quantity)  # add profit to profitgroup
                    added_costs = added_costs + (inventory.price_before_profit * inventory.quantity)
                inventory_usage.append({"id": inventory.id, "quantity": inventory.quantity})
                quantity = quantity - inventory.quantity  # decrease quantity
                #  db.session.delete(inventory)  # delete empty inventory
                inventory.quantity = 0
            else:
                inventory.quantity = inventory.quantity - quantity
                inventory_usage.append({"id": inventory.id, "quantity": quantity})
                break
        db.session.commit()
    return {"costs": added_costs, "inventory_usage": inventory_usage}


def add_to_inventory(product_id, quantity):
    p = Product.query.get(product_id)
    inventory = find_newest_inventory(product_id)
    if inventory is None:
        inventories = Inventory.query.filter(Inventory.product_id == product_id).all()
        if len(inventories) == 0:
            inventory = Inventory(product_id=product_id, timestamp=datetime.utcnow(), price_before_profit=0.0,
                                  quantity=0, note="Extra inventaris")
            db.session.add(inventory)
        elif type(inventories) is Inventory:
            inventory = Inventory
        else:
            inventory = inventories[-1]
    inventory.quantity = inventory.quantity + quantity
    db.session.commit()


def fix_negative_inventory(p_id):
    neg_inv = Inventory.query.filter(Inventory.product_id == p_id, Inventory.quantity < 0).all()
    if type(neg_inv) is Inventory:
        neg_inv = [neg_inv]

    for n in neg_inv:
        print("N: " + neg_inv.__repr__())
        pos_inv = Inventory.query.filter(and_(
            Inventory.product_id == p_id,
            Inventory.quantity > 0,
            Inventory.timestamp > n.timestamp
        )).all()
        print("P: " + pos_inv.__repr__())
        if type(pos_inv) is Inventory:
            pos_inv = [pos_inv]
        for p in pos_inv:
            fix_neg_inv(n, p)
            if n.quantity == 0:
                break


def correct_inventory(json):
    for i in json:
        p = Product.query.get(i['product_id'])
        diff = float(i['stock']) - float(calcStock(p.id))
        if diff < 0:
            for g_id in i['groups']:
                g = Usergroup.query.get(g_id)
                g.profit = g.profit + diff * p.price / len(i['groups'])
                db.session.commit()
                g = None
            take_from_inventory(None, p.id, -diff)
        elif diff > 0:
            add_to_inventory(p.id, diff)
            inv = find_newest_inventory()
            for g_id in i['groups']:
                g = Usergroup.query.get(g_id)
                g.profit = g.profit + diff * inv.price_before_profit / len(i['groups'])
                db.session.commit()
                g = None
    return "Inventaris correctie succesvol doorgevoerd!", "success"


def payout_profit(usergroup_id, amount, password):
    if password != app.config['ADMIN_PASSWORD']:
        return "Verificatiecode is ongeldig. Probeer het opnieuw", "danger"

    usergroup = Usergroup.query.get(usergroup_id)
    if amount > usergroup.profit:
        return "Het uit te keren bedrag is groter dan de opgebouwde winst! Kies een lager bedrag", "danger"
    if amount == 0:
        return "Het gekozen bedrag is ongeldig"

    usergroup.profit = usergroup.profit - amount
    db.session.commit()
    return "€ {} winst van {} uitgekeerd uit Tikker".format(str('%.2f' % usergroup.profit),
                                                            usergroup.name), "success"


def calcStock(product_id):
    inventories = Inventory.query.filter(and_(Inventory.product_id == product_id, Inventory.quantity != 0))
    sum = 0
    for i in inventories:
        sum = sum + i.quantity
    return sum


def rollback():
    db.session.rollback()


def force_edit():
    users = [1, 3]
    print(User.query.filter(User.id.in_(users)).all())


def is_birthday():
    today = datetime.today()
    days_in_year = 365.2425
    birthdays = []
    for u in User.query.all():
        bday = datetime(today.year, u.birthday.month, u.birthday.day)
        diff = (today - bday).days
        if 0 <= diff <= 7:
            age = int((today - u.birthday).days / days_in_year)
            birthdays.append({"user": u, "age": age})
    return birthdays
