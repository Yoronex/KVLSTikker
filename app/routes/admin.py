from datetime import datetime, timedelta

from flask_breadcrumbs import register_breadcrumb
from sqlalchemy import Integer, and_

from app.routes import *
from app import statshandler, socket, dbhandler, round_up, round_down, AttrDict


@app.route('/admin', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin', 'Beheerderspaneel', order=1)
def admin():
    check_if_local_machine()

    products = [AttrDict(p._asdict()) for p in db.session.query(Product.name, Product.inventory_warning,
                                                                func.sum(Inventory.quantity.cast(Integer)).label('quantity'),
                                                                func.sum(Inventory.quantity *
                                                                         Inventory.price_before_profit)
                                                                .label('inventory_value'))
        .filter(and_(Product.id == Inventory.product_id, Product.purchaseable == True))
        .group_by(Inventory.product_id).all()]

    total_p_value = sum([p['inventory_value'] for p in products])

    transactions = {'upgrades': Upgrade.query.count(), 'purchases': Purchase.query.count(),
                    'total': Transaction.query.count(),
                    'upgrades_value': db.session.query(func.sum(Upgrade.amount)).scalar(),
                    'purchases_value': db.session.query(func.sum(Purchase.amount * Purchase.price)).scalar()}
    transactions['revenue'] = transactions['upgrades_value'] - transactions['purchases_value']

    return render_template('admin/admin.html', title='Admin paneel', h1="Beheerderspaneel", Usergroup=Usergroup,
                           products=products, transactions=transactions, value=total_p_value), 200


@app.route('/admin/users', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.users', 'Gebruikersbeheer', order=2)
def admin_users():
    check_if_local_machine()

    form = UserRegistrationForm()
    filters = UsersFilterForm()

    query = User.query
    query = apply_filters(query)
    users = query.all()

    if form.validate_on_submit():
        check_if_not_view_only()
        alert = (dbhandler.adduser(form.name.data, form.email.data, form.group.data, form.profitgroup.data,
                                   form.birthday.data))
        flash(alert[0], alert[1])

        socket.update_stats()

        return redirect(url_for('admin_users'))
    flash_form_errors(form.errors)
    return render_template("admin/manusers.html", title="Gebruikersbeheer", h1="Gebruikersbeheer", users=users,
                           Usergroup=Usergroup, form=form, filters=filters), 200


@register_breadcrumb(app, '.admin.users.confirm', "Bevestigen", order=2)
@app.route('/admin/users/delete/<int:userid>')
def admin_users_delete(userid):
    check_if_local_machine()
    check_if_not_view_only()

    user = User.query.get(userid)
    group = Usergroup.query.get(user.usergroup_id)
    if user.balance == 0.0:
        message = "gebruiker " + user.name + "(van de groep " + group.name + ") wilt verwijderen? Alle historie gaat hierbij verloren!"
        agree_url = url_for("admin_users_delete_exec", userid=userid)
        return_url = url_for("admin_users")
        return render_template("verify.html", title="Bevestigen", message=message, agree_url=agree_url,
                               return_url=return_url), 200
    else:
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))


@app.route('/admin/users/delete/<int:userid>/exec')
def admin_users_delete_exec(userid):
    check_if_local_machine()
    check_if_not_view_only()

    if (User.query.get(userid).balance != 0.0):
        flash("Deze gebruiker heeft nog geen saldo van € 0!", "danger")
        return redirect(url_for('admin_users'))
    # alert = (dbhandler.deluser(userid))
    # flash(alert[0], alert[1])
    flash("Wegens enkele ontdekte fouten in Tikker is het verwijderen van gebruikers tijdelijk uitgeschakeld", "danger")

    socket.update_stats()

    return redirect(url_for('admin_users'))


@app.route('/admin/transactions')
@register_breadcrumb(app, '.admin.transactions', 'Transactiebeheer', order=2)
def admin_transactions():
    check_if_local_machine()

    query = Transaction.query
    query = apply_filters(query)

    pagination = calculate_pagination_with_basequery(query, request)
    transactions = query.limit(pagination['pageSize']).offset(pagination['offset']).all()[::-1]
    filters = TransactionFilterForm()

    return render_template('admin/mantransactions.html', title="Transactiebeheer", h1="Alle transacties", User=User,
                           transactions=transactions, Purchase=Purchase, Upgrade=Upgrade, pag=pagination,
                           Product=Product, filters=filters), 200


@register_breadcrumb(app, '.admin.transactions.confirm', "Bevestigen", order=2)
@app.route('/admin/transactions/delete/<int:tranid>')
def admin_transactions_delete(tranid):
    check_if_local_machine()
    check_if_not_view_only()

    transaction = Transaction.query.get(tranid)
    u = User.query.get(transaction.user_id)
    if transaction.purchase_id is not None:
        purchase = Purchase.query.get(transaction.purchase_id)
        product = Product.query.get(purchase.product_id)
        message = "transactie met ID " + "{} ({}x {} voor {})".format(str(transaction.id),
                                                                      str(round_up(purchase.amount)), product.name,
                                                                      u.name) + " wilt verwijderen?"
    else:
        upgr = Upgrade.query.get(transaction.upgrade_id)
        message = "transactie met ID " + "{} ({} € {} voor {})".format(str(transaction.id), upgr.description,
                                                                       round_up(upgr.amount),
                                                                       u.name) + " wilt verwijderen?"
    agree_url = url_for("admin_transactions_delete_exec", tranid=tranid)
    return_url = url_for("admin_transactions")
    return render_template("verify.html", title="Bevestigen", message=message, agree_url=agree_url,
                           return_url=return_url), 200


@app.route('/admin/transactions/delete/<int:tranid>/exec')
def admin_transactions_delete_exec(tranid):
    check_if_local_machine()
    check_if_not_view_only()

    alert = (dbhandler.deltransaction(tranid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_transactions'))


@app.route('/admin/drinks', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks', 'Productbeheer', order=2)
def admin_drinks():
    check_if_local_machine()
    form = DrinkForm()
    filters = ProductFilterForm()

    query = Product.query
    query = apply_filters(query)
    products = query.order_by(Product.order.asc()).all()

    if request.method == "POST":
        check_if_not_view_only()
        if form.validate_on_submit():
            alert = (
                dbhandler.adddrink(form.name.data, float(form.price.data), form.category.data, int(form.pos.data) + 1,
                                   form.image.data, form.hoverimage.data, form.recipe.data, form.inventory_warning.data,
                                   float(form.alcohol.data), form.volume.data, form.unit.data))
            flash(alert[0], alert[1])

            socket.update_stats()

            return redirect(url_for('admin_drinks'))
        else:
            flash(form.errors, "danger")
    flash_form_errors(form.errors)
    return render_template('admin/mandrinks.html', title="Productbeheer", h1="Productbeheer", Product=Product,
                           products=products, form=form, filters=filters), 200


def view_admin_drink_dlc(*args, **kwargs):
    drink_id = request.view_args['drinkid']
    product = Product.query.get(drink_id)
    return [{'text': product.name, 'url': url_for('admin_drinks_edit', drinkid=drink_id)}]


@app.route('/admin/drinks/edit/<int:drinkid>', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.drinks.id', '', dynamic_list_constructor=view_admin_drink_dlc, order=3)
def admin_drinks_edit(drinkid):
    check_if_local_machine()
    check_if_not_view_only()

    form = ChangeDrinkForm()
    form2 = ChangeDrinkImageForm()
    recipe = ""
    product = Product.query.get(drinkid)
    if product.recipe_input is not None:
        for key, value in product.recipe_input.items():
            recipe = recipe + str(value) + "x" + str(key) + ", "

    if form.submit1.data and form.validate_on_submit():
        alert = (dbhandler.editdrink_attr(drinkid, form.name.data, float(form.price.data),
                                          form.category.data, int(form.pos.data) + 1,
                                          form.purchaseable.data, form.recipe.data, int(form.inventory_warning.data),
                                          float(form.alcohol.data), int(form.volume.data), form.unit.data))
        flash(alert[0], alert[1])

        socket.update_stats()

        return redirect(url_for('admin_drinks'))
    if form2.submit2.data and form2.validate_on_submit():
        alert = (dbhandler.editdrink_image(drinkid, form2.image.data, form2.hoverimage.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_drinks'))
    flash_form_errors(form.errors)
    flash_form_errors(form2.errors)
    return render_template('admin/editdrink.html', title="{} bewerken".format(product.name),
                           h1="Pas {} (ID: {}) aan".format(product.name, product.id), product=product, form=form,
                           form2=form2, recipe=recipe[:-2]), 200


@app.route('/admin/drinks/delete/<int:drinkid>')
def admin_drinks_delete(drinkid):
    check_if_local_machine()
    check_if_not_view_only()

    alert = (dbhandler.deldrink(drinkid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_drinks'))


@app.route('/admin/usergroups', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.usergroups', 'Groepenbeheer', order=2)
def admin_usergroups():
    form = UserGroupRegistrationForm()
    if form.validate_on_submit():
        check_if_not_view_only()
        check_if_local_machine()
        alert = (dbhandler.addusergroup(form.name.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_usergroups'))
    flash_form_errors(form.errors)
    return render_template("admin/manusergroups.html", title="Groepen", h1="Groepenbeheer", form=form,
                           Usergroup=Usergroup), 200


@register_breadcrumb(app, '.admin.usergroups.confirm', 'Bevestigen', order=2)
@app.route('/admin/usergroups/delete/<int:usergroupid>')
def admin_usergroups_delete(usergroupid):
    check_if_local_machine()
    check_if_not_view_only()

    usergroup = Usergroup.query.get(usergroupid)
    users = usergroup.users.all()
    if len(users) == 0:
        message = "groep " + usergroup.name + " wilt verwijderen?"
        agree_url = url_for("admin_usergroups_delete_exec", usergroupid=usergroupid)
        return_url = url_for("admin_usergroups")
        return render_template("verify.html", title="Bevestigen", message=message, agree_url=agree_url,
                               return_url=return_url), 200
    else:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))


@app.route('/admin/usergroups/delete/<int:usergroupid>/exec')
def admin_usergroups_delete_exec(usergroupid):
    check_if_local_machine()
    check_if_not_view_only()

    if len(Usergroup.query.get(usergroupid).users.all()) != 0:
        flash("Deze groep heeft nog gebruikers! Verwijder deze eerst.", "danger")
        return redirect(url_for('admin_usergroups'))
    alert = (dbhandler.delusergroup(usergroupid))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_usergroups'))


@register_breadcrumb(app, '.admin.inventory', 'Inventarisbeheer', order=2)
@app.route('/admin/inventory/', methods=['GET', 'POST'])
def admin_inventory():
    check_if_local_machine()
    form = AddInventoryForm()
    if form.validate_on_submit():
        check_if_not_view_only()
        alert = (dbhandler.add_inventory(int(form.product.data), form.quantity.data,
                                         float(form.purchase_price.data), form.note.data))
        flash(alert[0], alert[1])
        return redirect(url_for('admin_inventory'))

    flash_form_errors(form.errors)
    return render_template("admin/maninventory.html", title="Inventarisbeheer", h1="Inventarisbeheer",
                           backurl=url_for('index'), Product=Product,
                           Inventory=Inventory, form=form), 200


@register_breadcrumb(app, '.admin.inventorycorrect', 'Inventariscorrectie', order=2)
@app.route('/admin/inventory/correct', methods=['GET', 'POST'])
def admin_correct_inventory():
    check_if_local_machine()
    check_if_not_view_only()
    products = [p.serialize for p in Product.query.filter(Product.recipe_input == None).all()]
    for p in products:
        p['stock'] = dbhandler.calcStock(p['id'])

    if request.method == 'POST':
        result = dbhandler.correct_inventory(request.get_json())
        if type(result) is tuple:
            flash(result[0], result[1])
        return redirect(url_for('admin'), code=302)

    inventories = [i.serialize for i in Inventory.query.filter(Inventory.quantity != 0).all()]
    usergroup_ids = {g.id: g.name for g in Usergroup.query.all()}
    return render_template("admin/inventorycorrection.html", title="Inventaris correctie", h1="Inventaris correctie",
                           Product=Product, products=products, Usergroup=Usergroup, inventories=inventories,
                           usergroup_ids=usergroup_ids)


@app.route('/admin/upgrade', methods=['GET', 'POST'])
@register_breadcrumb(app, '.admin.upgrade', 'Opwaarderen', order=2)
def upgrade():
    check_if_local_machine()
    check_if_not_view_only()

    # Create the two forms that will be included
    upgr_form = UpgradeBalanceForm()
    decl_form = DeclarationForm()

    # If one of the forms has been submitted
    if (upgr_form.upgr_submit.data and upgr_form.validate_on_submit()) or \
            (decl_form.decl_submit.data and decl_form.validate_on_submit()):
        # Change the decimal amount to a float
        amount = float(upgr_form.amount.data)

        # The amount cannot be negative!
        if amount < 0.0:
            flash("Opwaardering kan niet negatief zijn!", "danger")
            return render_template('admin/upgrade.html', title='Opwaarderen', h1="Opwaarderen",
                                   upgr_form=upgr_form, decl_form=decl_form)

        # If the upgrade form has been filled in...
        if upgr_form.upgr_submit.data and upgr_form.validate_on_submit():
            # Add the upgrade to the database
            upgrade = (dbhandler.addbalance(int(upgr_form.user.data), "Opwaardering", amount))
            # Get the user for the messages that now follow
            user = User.query.get(upgrade.user_id)

            socket.send_transaction("{} heeft opgewaardeerd met € {}"
                                    .format(user.name, str("%.2f" % upgrade.amount).replace(".", ",")))
            flash("Gebruiker {} heeft succesvol opgewaardeerd met € {}"
                  .format(user.name,str("%.2f" % upgrade.amount).replace(".", ",")), "success")

        # If the declaration form has been filled in
        else:
            # Add the upgrade to the database
            upgrade = (dbhandler.add_declaration(int(decl_form.user.data), decl_form.description.data,
                                                 amount, int(decl_form.payer.data)))
            # Get the user for the messages that now follow
            user = User.query.get(upgrade.user_id)

            socket.send_transaction("{} heeft € {} teruggekregen ({})"
                                    .format(user.name, str("%.2f" % upgrade.amount).replace(".", ","),
                                            upgrade.description))
            flash("Gebruiker {} heeft succesvol € {} teruggekregen voor: {}"
                  .format(user.name, str("%.2f" % upgrade.amount).replace(".", ","), upgrade.description), "success")

        # Update the daily stats
        socket.update_stats()

        return redirect(url_for('admin'))

    # Show errors if there are any
    flash_form_errors(upgr_form.errors)
    flash_form_errors(decl_form.errors)
    return render_template('admin/upgrade.html', title='Opwaarderen', h1="Opwaarderen",
                           upgr_form=upgr_form, decl_form=decl_form)


@register_breadcrumb(app, '.admin.profit', 'Winst uitkeren', order=2)
@app.route('/admin/profit', methods=['GET', 'POST'])
def payout_profit():
    check_if_local_machine()
    form = PayOutProfitForm()
    if form.validate_on_submit():
        check_if_not_view_only()
        alert = dbhandler.payout_profit(int(form.usergroup.data), float(form.amount.data), form.verification.data)
        flash(alert[0], alert[1])
        return redirect(url_for('payout_profit'))
    flash_form_errors(form.errors)
    return render_template("admin/manprofit.html", title="Winst uitkeren", h1="Winst uitkeren", Usergroup=Usergroup,
                           form=form), 200


@register_breadcrumb(app, '.admin.borrelmode', "Borrel Modus", order=2)
@app.route('/admin/borrelmode', methods=['GET', 'POST'])
def borrel_mode():
    check_if_local_machine()
    check_if_not_view_only()

    form = BorrelModeForm()
    if form.validate_on_submit():
        dbhandler.set_borrel_mode(form.products.data, form.user.data, form.amount.data)
        flash('Borrel modus succesvol aangezet!', "success")

    # Get general data if borrel mode is still enabled
    borrel_data = dbhandler.borrel_mode()
    # Construct a list of products
    if borrel_data is not None:
        product_string = ""
        # For every product, add its name to the string
        for p in dbhandler.borrel_mode_drinks:
            product_string += Product.query.get(p).name + ", "
        # If there are products...
        if len(product_string) > 0:
            # Remove the final comma and space from the string
            product_string = product_string[:-2]
        # Add this string to the borrel data object
        borrel_data['products'] = product_string
        # Add whether borrel mode is still enabled
        borrel_data['enabled'] = dbhandler.borrel_mode_enabled

    flash_form_errors(form.errors)
    return render_template('admin/borrelmode.html', title="Borrel Modus beheren", h1="Borrel modus", form=form,
                           borrel_data=borrel_data), 200


@app.route('/admin/borrelmode/disable', methods=['GET'])
def disable_borrel_mode():
    check_if_local_machine()
    check_if_not_view_only()
    dbhandler.borrel_mode_enabled = False
    flash("Borrel mode uitgeschakeld", "success")
    return redirect(url_for('borrel_mode'))


@register_breadcrumb(app, '.admin.soundboard', 'Soundboard', order=2)
@app.route('/admin/soundboard', methods=['GET', 'POST'])
def admin_soundboard():
    check_if_local_machine()
    form = SoundBoardForm()
    if form.validate_on_submit():
        check_if_not_view_only()
        dbhandler.add_sound(form.name.data, form.key.data, form.code.data, form.file.data)
        flash('Geluid {} succesvol toegevoegd'.format(form.name.data), 'success')

    flash_form_errors(form.errors)
    return render_template('admin/mansounds.html', title="Beheer soundboard", h1="Beheer soundboard", form=form,
                           Sound=Sound)


@register_breadcrumb(app, '.admin.soundboard.confirm', 'Bevestigen', order=3)
@app.route('/admin/soundboard/delete/<int:sound_id>')
def admin_soundboard_delete(sound_id):
    check_if_local_machine()
    check_if_not_view_only()
    sound = Sound.query.get(sound_id)
    message = "geluid " + sound.name + " wilt verwijderen?"
    agree_url = url_for("admin_soundboard_delete_exec", sound_id=sound_id)
    return_url = url_for("admin_soundboard")
    return render_template("verify.html", title="Bevestigen", message=message, agree_url=agree_url,
                           return_url=return_url), 200


@app.route('/admin/soundboard/delete/<int:sound_id>/exec')
def admin_soundboard_delete_exec(sound_id):
    check_if_local_machine()
    check_if_not_view_only()
    alert = (dbhandler.del_sound(sound_id))
    flash(alert[0], alert[1])
    return redirect(url_for('admin_soundboard'))


def merge_queries(target_query, source_query, fields, defaults, conditions, calculations):
    # Parse the source query from a list of dictionaries to a dictionary, where the ID is the key
    source = {}
    for s in source_query:
        source[s['id']] = s

    # For each row in the target query...
    for t in target_query:
        # Check if the ID exists in both queries
        if t['id'] in source.keys():
            # If this is the case, we will merge each field
            for i in range(0, len(fields)):
                # First, check if there is a condition that should hold. If there is one,
                # check whether that condition actually holds
                if conditions[i] is None or conditions[i](t):
                    # If the condition holds and we do not have to do any calculations for that field...
                    if calculations[i] is None:
                        # Add the field to the target row
                        t[fields[i]] = source[t['id']][fields[i]]
                    # If we need to do a calculation
                    else:
                        # Add the result of the calculation in the field to the target row
                        t[fields[i]] = calculations[i](t, source[i])
                # If the condition does not hold...
                else:
                    # Add the default value to the target row
                    t[fields[i]] = defaults[i]
        # If the ID does not exist in the source query...
        else:
            # Simply add the default value for each field to the target row
            for i in range(0, len(fields)):
                t[fields[i]] = defaults[i]

    # Return the target query, which is now merged with the source query
    return target_query


@register_breadcrumb(app, '.admin.treasurer', 'Penningmeester', order=2)
@app.route('/admin/treasurer')
def admin_treasurer():
    check_if_local_machine()

    filters_inv = InventoryFilterForm()
    filters_users = UsersFilterForm()

    now = datetime.now()
    three_months_ago = now - timedelta(days=7 * 12)

    '''
    Query the data from the database and calculate other necessary values
    '''

    # Query the inventory quantity left for each product
    rawquery = db.session.query(Product.name, Product.id, Product.category, Product.inventory_warning,
                                func.sum(Inventory.quantity.cast(Integer)).label('quantity'),
                                func.sum(Inventory.quantity * Inventory.price_before_profit)
                                .label('inventory_value'))\
        .filter(and_(Product.id == Inventory.product_id, Product.purchaseable == True,
                     Product.id != dbhandler.settings['dinner_product_id']))\
        .group_by(Inventory.product_id)

    # Apply the filters to the query
    if 'f_product_category' in request.args and request.args.get('f_product_category') != 'all':
        rawquery = rawquery.filter(Product.category == request.args.get('f_product_category'))
    # Convert the result from a list of tuples to a list of dicts
    products = [p._asdict() for p in rawquery.all()]

    # Calculate the total value of the inventory
    total_p_value = sum([p['inventory_value'] for p in products])

    # Query the consumption of each product per week over a period of 12 weeks
    purchases = db.session.query(Purchase.product_id.label('id'),
                                 func.sum(Purchase.amount / 12).label('per_week'))\
        .filter(Purchase.round == False, Purchase.timestamp > three_months_ago)\
        .group_by(Purchase.product_id).all()
    # Convert the result to a list of dicts
    purchases = [p._asdict() for p in purchases]

    # Function to calculate when the stock will be empty
    def stock_empty(p, source):
        return datetime.now() + timedelta(days=int(p['quantity'] / p['per_week'] * 7))

    # Merge the products and purchases table
    products = merge_queries(products, purchases, ['per_week', 'stock_empty'], [0, None], [None, None],
                             [None, stock_empty])

    '''
    Create the analysis graphs
    '''

    # Create two empty lists for parsed data for the graphs
    qdata, vdata = [], []
    # For each product...
    for p in products:
        # Add a tuple to the lists
        qdata.append((p['id'], p['name'], round(p['quantity'])))
        vdata.append((p['id'], p['name'], round_down(p['inventory_value'])))
    # Process the data lists for the graphs on the page
    product_q, product_v = {}, {}
    product_q['ids'], product_q['value'], product_q['labels'] = statshandler.topall(None, qdata)
    product_v['ids'], product_v['value'], product_v['labels'] = statshandler.topall(None, vdata)

    '''
    Create the category graphs 
    '''

    # Create two empty lists for parsed data for the graphs
    qdata, vdata = [], []
    # Create a dictionary to store all the cumulative data
    categories = {}
    # Loop over all products
    for p in products:
        # If a product category is not yet in the dictionary...
        if p['category'] not in categories:
            # Add it with the corresponding values
            categories[p['category']] = {'quantity': p['quantity'],
                                         'value': p['inventory_value']}
        # If is is, increment the values in the dictionary
        else:
            categories[p['category']]['quantity'] += p['quantity']
            categories[p['category']]['value'] += p['inventory_value']

    # Remove the empty category if it is present
    if "" in categories:
        categories.pop("")

    # Add all the data to the two lists
    for category, v in categories.items():
        qdata.append((0, category, round(v['quantity'])))
        vdata.append((0, category, round(v['value'])))
    # Parse the data into readable data for the graphs
    category_q, category_v = {}, {}
    category_q['ids'], category_q['value'], category_q['labels'] = statshandler.topall(None, qdata)
    category_v['ids'], category_v['value'], category_v['labels'] = statshandler.topall(None, vdata)

    '''
    Query the users table
    '''

    # The base query for all the users
    users_query = db.session.query(User.id, User.name, User.balance, Usergroup.name.label('group'))\
        .filter(User.usergroup_id == Usergroup.id)\
        .order_by(User.usergroup_id)

    # Stolen from the function above, because the filter function cannot be called.
    # There are two tables on this page and applying filters on both causes problems
    if 'f_user_usergroup' in request.args and int(request.args.get('f_user_usergroup')) > 0:
        users_query = users_query.filter(User.usergroup_id == int(request.args.get('f_user_usergroup')))
    if 'f_user_profitgroup' in request.args and int(request.args.get('f_user_profitgroup')) > 0:
        users_query = users_query.filter(User.profitgroup_id == int(request.args.get('f_user_profitgroup')))
    # Finish the query and convert all items to dictionaries
    users = [u._asdict() for u in users_query.all()]

    #  Query the amount every user spends per week (to merge later)
    purchase1 = db.session.query(Purchase.user_id.label('id'),
                                 func.sum(Purchase.amount * Purchase.price / 12).label('per_week'))\
        .filter(Purchase.timestamp > three_months_ago).group_by(Purchase.user_id).all()
    # Convert it to a dictionary
    purchase1 = [p._asdict() for p in purchase1]

    # Query the average balance of every user during three months
    transaction1 = db.session.query(Transaction.user_id.label('id'),
                                    func.avg(Transaction.newbal).label('average_balance'))\
        .filter(Transaction.timestamp > three_months_ago).group_by(Transaction.user_id).all()
    # Convert it to a dictionary
    transaction1 = [t._asdict() for t in transaction1]

    # Query the last time the user had a positive balance (earliest from now on)
    transaction2 = db.session.query(Transaction.user_id.label('id'), Transaction.timestamp.label('last_positive'))\
        .filter(Transaction.newbal > 0).group_by(Transaction.user_id).all()
    #  Convert it to a dictionary
    transaction2 = [t._asdict() for t in transaction2]

    # Condition that will be used later when merging
    def positive_balance(user):
        if user['balance'] > 0:
            return True
        return False

    # Function to calculate the (expected) time until the user has no more balance
    def no_balance_left(u, source):
        return datetime.now() + timedelta(days=int(u['balance'] / u['per_week'] * 7))

    # Merge all the three seperate queries with the users query
    users = merge_queries(users, purchase1, ['per_week', 'no_balance_left'], [0, None], [None, positive_balance],
                          [None, no_balance_left])
    users = merge_queries(users, transaction1, ['average_balance'], [None], [None], [None])
    users = merge_queries(users, transaction2, ['last_positive'], [datetime.now()], [None], [None])

    # Because not every user has an average balance and because it is hard to parameterize
    # in the merge_queries function above, we add this average balance manually
    for u in users:
        if u['average_balance'] is None:
            u['average_balance'] = u['balance']

    # Calculate the sum of all the balances and other numbers
    total_u_balance = sum([u['balance'] for u in users])
    total_u_average = sum([u['average_balance'] for u in users])
    total_u_per_week = sum([u['per_week'] for u in users])

    '''
    Finalize
    '''

    # Calculate the render time
    render_time = int((datetime.now() - now).microseconds / 1000)

    return render_template('admin/treasurer.html', title='Penno Panel', h1='Penno Panel',
                           products=products, filters_inv=filters_inv, filters_users=filters_users,
                           total_p_value=total_p_value, product_q=product_q, product_v=product_v, category_q=category_q,
                           category_v=category_v, rendertime=render_time, users=users,
                           total_u_balance=total_u_balance, total_u_average=total_u_average,
                           total_u_per_week=total_u_per_week), 200



@app.route('/admin/recalcmax')
def recalculate_max_stats():
    check_if_local_machine()
    check_if_not_view_only()

    transactions = Transaction.query.all()
    begindate = datetime(year=2019, month=7, day=1, hour=12, minute=0, second=0)
    for t in transactions:
        begindate2 = statshandler.get_yesterday_for_today(t.timestamp)
        if begindate2 != begindate:
            begindate = begindate2
            statshandler.reset_daily_stats()
        statshandler.update_daily_stats("euros", t.balchange)

        if t.purchase_id is not None:
            p = Purchase.query.get(t.purchase_id)
            if p.round:
                statshandler.update_daily_stats("rounds", 1)
            statshandler.update_daily_stats_drinker(p.user_id)
            if p.price > 0:
                statshandler.update_daily_stats_product(p.product_id, p.amount)
            statshandler.update_daily_stats("purchases", 1)
    statshandler.update_daily_stats("products", Product.query.filter(Product.purchaseable == True).count())
    statshandler.update_daily_stats("users", User.query.count())
    socket.update_stats()
    return redirect(url_for("index"))
