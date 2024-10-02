import csv
import xmlrpc.client

url = 'http://localhost:8069'
db = 'v16_legere_pharmaceuticals'
username = 'admin'
password = 'admin'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

csv_file = '/home/sagar/Desktop/update_product_legere_order_part.csv'

csv_data = csv.DictReader(open(csv_file))

for row in csv_data:
    print ("================Data================", row)
    product_name = row.get('Name')
    product_number = row.get('ProdNum')
    product_number2 = row.get('ProdNum2')

    product = models.execute_kw(db, uid, password, 'product.product', 'search', [[['name', '=', product_name.strip()]]], {'limit': 1})
    print ("================Product================", product)
    if product:
        legere_order_parts = models.execute_kw(db, uid, password, 'legere.order.part', 'search', [[['ProductNumber', '!=', False], '|', ['ProductNumber', '=', product_number], ['ProductNumber', '=', product_number2]]])
        print ("================Order Parts================", legere_order_parts)
        if legere_order_parts:
            models.execute_kw(db, uid, password, 'legere.order.part', 'write', [legere_order_parts, {'product_id': product[0]}])