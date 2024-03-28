# Legere    
## Modules
### Legere Custom Modules
#### Installed
* `legere_custom`
* `legere_hubspot`
* `legere_legacy`
* `legere_mrp`
* `legere_nacha_approvals`
  * Add approval process to batch payments (i.e., download NACHA file)
  * Extends `stride_billpay`
  * *TODO: Configure to use in Production*
* `legere_sales`
* `legere_sales_commission`
* `legere_stock`

#### Not Installed
* `legere_account_followup`
  * Started but not completed or installed
  * Idea was to prevent followup from going out
* `legere_pricelist_import_script`
  * Python script to import the pricelist
  * Not an installable module

### Stride Custom Modules
#### Installed
* `custom_services_flow`
* `stride_billpay`
* `stride_delivery`
* `stride_package_consume`
* `stride_payment_sales`
* `stride_payment_sales_authorize`
* `stride_payment_token`
* `stride_payments`
* `stride_payments_authorize_ee`
* `stride_payments_statements_ee`

#### Not Installed
* `stride_printnode_base`
  * Module to help print labels
  * Used `zebra.bat` instead to handle it on windows system

### OCA (Odoo Community Association)
* [stock_no_negative](https://github.com/OCA/stock-logistics-workflow/tree/16.0/stock_no_negative)
* [web_ir_actions_act_multi](https://github.com/OCA/web/tree/16.0/web_ir_actions_act_multi)