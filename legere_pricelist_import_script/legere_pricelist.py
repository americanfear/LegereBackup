import credentials
from xmlrpc import client as xmlrpclib
import csv

common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(credentials.url))
models = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(credentials.url))
uid = common.login(credentials.db, credentials.user, credentials.token)
pricelist_id = 1

csv_file = './legere_pricelist_import_script/legere_pricelist.csv'
csv_data = csv.DictReader(open(csv_file, encoding='utf-8'))
for row in csv_data:
    product_id = row.get('id')
    if product_id:
        product = models.execute_kw(credentials.db, uid, credentials.token, 'product.product', 'search',
                                    [[['id', '=', product_id]]], {'limit': 1})
        if product:
            product_id = product[0]
            if row.get('12') and float(row['12']) != 0:
                data_write = [{
                    'pricelist_id': pricelist_id,
                    'applied_on': '0_product_variant',
                    'product_id': product_id,
                    'min_quantity': '12',
                    'fixed_price': float(row['12'])
                }]
                models.execute_kw(credentials.db, uid, credentials.token, 'product.pricelist.item', 'create', data_write)
            if row.get('24') and float(row['24']) != 0:
                data_write = [{
                    'pricelist_id': pricelist_id,
                    'applied_on': '0_product_variant',
                    'product_id': product_id,
                    'min_quantity': '24',
                    'fixed_price': float(row['24'])
                }]
                models.execute_kw(credentials.db, uid, credentials.token, 'product.pricelist.item', 'create', data_write)
            if row.get('50') and float(row['50']) != 0:
                data_write = [{
                    'pricelist_id': pricelist_id,
                    'applied_on': '0_product_variant',
                    'product_id': product_id,
                    'min_quantity': '50',
                    'fixed_price': float(row['50'])
                }]
                models.execute_kw(credentials.db, uid, credentials.token, 'product.pricelist.item', 'create', data_write)
            if row.get('100') and float(row['100']) != 0:
                data_write = [{
                    'pricelist_id': pricelist_id,
                    'applied_on': '0_product_variant',
                    'product_id': product_id,
                    'min_quantity': '100',
                    'fixed_price': float(row['100'])
                }]
                models.execute_kw(credentials.db, uid, credentials.token, 'product.pricelist.item', 'create', data_write)