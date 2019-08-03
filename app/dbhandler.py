from app import app, db, dbhandler
from app.models import User, Usergroup, Product, Purchase, Upgrade, Transaction, Inventory
from werkzeug.utils import secure_filename
from datetime import datetime
import os

class dbhandler():
    def getdb(self):
        global db_obj
        if db_obj is None:
            db_obj = dbhandler()
        return db_obj

    def remove_existing_file(self, filename):
        file_loc = os.path.join(app.config["UPLOAD_FOLDER"] + filename)
        if os.path.exists(file_loc):
            os.remove(file_loc)

    def create_filename(self, product, old_filename, image, character):
        filename, file_extension = os.path.splitext(secure_filename(image.filename))
        filename = str(product.id) + character + "-" + str(int(old_filename.split('-')[1]) + 1) + file_extension
        self.remove_existing_file(filename)
        return filename

    def addpurchase(self, drink_id, user_id, quantity):
        if type(quantity) is float:
            quantity = float(round(quantity * 100)) / 100
        drink = Product.query.get(drink_id)
        user = User.query.get(user_id)

        if drink.components is None:
            self.take_from_inventory(user, drink_id, quantity)
        else:
            for key, val in drink.components.items():
                self.take_from_inventory(user, key, val * quantity)

        user.balance = user.balance - float(drink.price) * quantity
        purchase = Purchase(user_id=user.id, timestamp=datetime.now(), product_id=drink.id, price=drink.price, amount=quantity)
        db.session.add(purchase)
        db.session.commit()
        balchange = -drink.price * quantity
        transaction = Transaction(user_id=user.id, timestamp=datetime.now(), purchase_id=purchase.id, balchange=balchange, newbal=user.balance)
        db.session.add(transaction)
        db.session.commit()
        return "{}x {} voor {} verwerkt".format(quantity, drink.name, user.name), "success"

    def addbalance(self, user_id, amount):
        upgrade = Upgrade(user_id=user_id, timestamp=datetime.now(), amount=amount)
        db.session.add(upgrade)
        db.session.commit()
        user = User.query.get(upgrade.user_id)
        user.balance = user.balance + float(amount)
        transaction = Transaction(user_id=user_id, timestamp=datetime.now(), upgrade_id=upgrade.id, balchange=upgrade.amount,
                                  newbal=user.balance)
        db.session.add(transaction)
        db.session.commit()
        return "Gebruiker {} heeft succesvol opgewaardeerd met €{}".format(user.name, str("%.2f" % upgrade.amount).replace(".", ",")), "success"

    def parse_recipe(self, recipe):
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
                    return "MEEP", "danger"
                data[0] = int(data[0])
                data[1] = int(data[1])
                if Product.query.get(data[1]) is None or Product.query.get(data[1]).purchaseable is False:
                    return "Product met ID {} bestaat niet of is niet beschikbaar!".format(str(data[1])), "danger"
                result_recipe[data[1]] = data[0]
            if len(result_recipe.items() <= 1):
                return "Een recept kan niet uit één type product bestaan!"
            return result_recipe
        return None

    def adddrink(self, name, price, image, hoverimage, recipe):
        result_recipe = self.parse_recipe(recipe)
        if type(result_recipe) is tuple:
            return result_recipe

        s_filename, s_file_extension = os.path.splitext(secure_filename(image.filename))
        if s_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
            return "Statische afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"
        if hoverimage != "":
            h_filename, h_file_extension = os.path.splitext(secure_filename(hoverimage.filename))
            if h_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
                return "Hover afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"

        product = Product(name=name, price=price, purchaseable=True, image="", hoverimage="", components=result_recipe)  # image="s" + s_file_extension, hoverimage="h" + h_file_extension)
        db.session.add(product)
        db.session.commit()

        if not os.path.exists(app.config["UPLOAD_FOLDER"]):
            os.makedirs(app.config["UPLOAD_FOLDER"])
        product.image = self.create_filename(product, str(product.id) + "s-0", image, "s")
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], product.image))

        if hoverimage == "":
            product.hoverimage = product.image
        else:
            product.hoverimage = self.create_filename(product, str(product.id) + "h-0", hoverimage, "h")
            hoverimage.save(os.path.join(app.config["UPLOAD_FOLDER"], product.hoverimage))
        db.session.commit()

        return "Product {} succesvol aangemaakt".format(product.name), "success"

    def adduser(self, name, group, profitgroup):
        user = User(name=name, usergroup_id=group, profitgroup_id=profitgroup)
        db.session.add(user)
        db.session.commit()
        return "Gebruiker {} succesvol geregistreerd".format(user.name), "success"

    def addusergroup(self, name):
        usergroup = Usergroup(name=name, )
        db.session.add(usergroup)
        db.session.commit()
        return "Groep {} succesvol aangemaakt".format(usergroup.name), "success"

    def deluser(self, user_id):
        user = User.query.get(user_id)
        for t in user.transactions.all():
            db.session.delete(t)
        for u in user.upgrades.all():
            db.session.delete(u)
        for p in user.purchases.all():
            db.session.delete(p)
        db.session.delete(user)
        db.session.commit()
        return "Gebruiker {} verwijderd".format(user.name), "success"

    def delpurchase(self, transaction_id):
        transaction = Transaction.query.get(transaction_id)
        if transaction.purchase_id is None:
            upgrade = Upgrade.query.get(transaction.upgrade_id)
            db.session.delete(upgrade)
        else:
            purchase = Purchase.query.get(transaction.purchase_id)
            db.session.delete(purchase)
        for t in Transaction.query.filter(Transaction.user_id == transaction.user_id, Transaction.timestamp > transaction.timestamp).all():
            t.newbal = t.newbal - transaction.balchange
        user = User.query.get(transaction.user_id)
        user.balance = user.balance - transaction.balchange
        db.session.delete(transaction)
        db.session.commit()
        return "Transactie met ID {} succesvol verwijderd!".format(transaction.id), "success"

    def deldrink(self, drink_id):
        product = Product.query.get(drink_id)
        product.purchaseable = False
        db.session.commit()
        return 'Product {} is niet meer beschikbaar'.format(product.name), "success"

    def delusergroup(self, usergroup_id):
        usergroup = Usergroup.query.get(usergroup_id)
        db.session.delete(usergroup)
        db.session.commit()
        return "Groep {} verwijderd".format(usergroup.name), "success"

    def editdrink_attr(self, product_id, name, price, purchaseable, recipe):
        result_recipe = self.parse_recipe(recipe)
        if type(result_recipe) is tuple:
            return result_recipe
        product = Product.query.get(product_id)
        product.name = name
        product.price = price
        product.purchaseable = purchaseable
        product.components = result_recipe
        db.session.commit()
        return "Product {} (ID: {}) succesvol aangepast!".format(product.name, product.id), "success"

    def editdrink_image(self, product_id, image, hoverimage):
        product = Product.query.get(product_id)
        print(image)
        print(hoverimage)
        if image != "":
            s_filename, s_file_extension = os.path.splitext(secure_filename(image.filename))
            if s_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
                return "Statische afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"
            product.image = self.create_filename(product, os.path.splitext(product.image)[0], image, "s")
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], product.image))
        if hoverimage != "":
            h_filename, h_file_extension = os.path.splitext(secure_filename(hoverimage.filename))
            if h_file_extension[1:] not in app.config["ALLOWED_EXTENSIONS"]:
                return "Hover afbeelding is niet van het correcte bestandstype (geen .png, .jpg, .bmp of .gif)", "danger"
            product.hoverimage = self.create_filename(product, os.path.splitext(product.image)[0], hoverimage, "h")
            hoverimage.save(os.path.join(app.config["UPLOAD_FOLDER"], product.hoverimage))
        db.session.commit()
        return "Afbeelding van product {} (ID: {}) succesvol aangepast!".format(product.name, product.id), "success"

    # -- Inventory management -- #

    def get_inventory_stock(self, product_id):
        if Product.query.get(product_id).components is None:
            return [self.get_inventory_stock_for_product(product_id)]
        else:
            result = []
            for key, value in Product.query.get(product_id).components.items():
                p = Product.query.get(key)
                stock = self.get_inventory_stock_for_product(key)
                stock["name"] = p.name
                stock["recipe_quantity"] = value
                result.append(stock)
            return result

    def get_inventory_stock_for_product(self, product_id):
        result = {}
        inventories = Inventory.query.filter(Inventory.product_id == product_id).all()
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

    def find_oldest_inventory(self, product_id):
        inventories = Inventory.query.filter(Inventory.product_id == product_id).all()
        if len(inventories) == 0:
            return None
        elif type(inventories) is Inventory:
            return inventories
        else:
            return inventories[0]

    def get_inventory(self, product_id):
        inventories = Inventory.query.filter(Inventory.product_id == product_id).all()
        sum = 0
        for i in inventories:
            sum = sum + i.quantity
        return sum

    def add_inventory(self, product_id, quantity, price_before_profit, note):
        inventory = self.find_oldest_inventory(product_id)
        if inventory is not None and inventory.quantity < 0:

            purchases = Purchase.query.filter(Inventory.product_id == product_id).all()
            filtered_purchases = []
            i = 0
            amount = 0

            if inventory.quantity >= -float(quantity):
                goal = 0
            else:
                goal = -(inventory.quantity + quantity)

            while amount < -inventory.quantity:
                i = i - 1
                t = purchases[i]
                amount = amount + t.amount
                filtered_purchases.append(t)

            product = Product.query.get(product_id)
            profit = product.price - price_before_profit
            old_quantity = -inventory.quantity
            j = 0

            while amount > goal:
                j = j - 1
                amount = amount - filtered_purchases[j].amount
                profitgroup = Usergroup.query.get(User.query.get(filtered_purchases[j].user_id).profitgroup_id)
                if amount >= goal:
                    profitgroup.profit = profitgroup.profit + (old_quantity - amount) * profit
                    old_quantity = amount
                else:
                    profitgroup.profit = profitgroup.profit + (filtered_purchases[j].amount - goal) * profit
                profitgroup = None


            if inventory.quantity + quantity < 0:
                inventory.quantity = inventory.quantity + quantity
            elif inventory.quantity + quantity == 0:
                db.session.delete(inventory)
            else:
                new_inventory = Inventory(product_id=product_id, quantity=quantity + inventory.quantity, price_before_profit=price_before_profit, note=note)
                db.session.delete(inventory)
                db.session.add(new_inventory)

        else:
            inventory = Inventory(product_id=product_id, quantity=float(quantity), price_before_profit=price_before_profit, note=note)
            db.session.add(inventory)

        db.session.commit()
        product = Product.query.get(product_id)
        return "{} {} toegevoegd aan inventaris!".format(str(quantity), product.name), "success"

    def take_from_inventory(self, user, product_id, quantity):
        product = Product.query.get(product_id)
        profitgroup = Usergroup.query.get(user.profitgroup_id)
        while 0 < quantity:
            inventory = self.find_oldest_inventory(product_id)
            if inventory is None:
                inventory = Inventory(product_id=product_id, quantity= float(- quantity), note="Noodinventaris")
                db.session.add(inventory)
                db.session.commit()
                break
            else:
                if quantity < inventory.quantity:
                    profit = product.price - inventory.price_before_profit
                    profitgroup.profit = profitgroup.profit + (profit * quantity)
                    inventory.quantity = inventory.quantity - quantity
                    break
                elif quantity >= inventory.quantity > 0.0:
                    profit = product.price - inventory.price_before_profit  # calculate profit
                    profitgroup.profit = profitgroup.profit + (profit * inventory.quantity)  # add profit to profitgroup
                    quantity = quantity - inventory.quantity  # decrease quantity
                    db.session.delete(inventory)  # delete empty inventory
                    db.session.commit()
                else:
                    inventory.quantity = inventory.quantity - quantity
                    break

    def payout_profit(self, usergroup_id, amount, password):
        if password != app.config['ADMIN_PASSWORD']:
            return "Verificatiecode is ongeldig. Probeer het opnieuw", "danger"

        usergroup = Usergroup.query.get(usergroup_id)
        if amount > usergroup.profit:
            return "Het uit te keren bedrag is groter dan de opgebouwde winst! Kies een lager bedrag", "danger"
        if amount == 0:
            return "Het gekozen bedrag is ongeldig"

        usergroup.profit = usergroup.profit - amount
        db.session.commit()
        return "€ {} winst van {} uitgekeerd uit Tikker".format(str('%.2f' % usergroup.profit), usergroup.name), "success"

    def force_edit(self):
        for p in Product.query.all():
            if p.image == str(p.id) + ".jpg":
                p.image = ".jpg"
        db.session.commit()




