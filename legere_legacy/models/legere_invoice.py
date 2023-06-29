from odoo import models, api, _, fields

class LegereInvoice(models.Model):
    _name = "legere.invoice"
    _description = "Invoices"
    _rec_name = "InvoiceNumber"

    InvoiceNumber = fields.Char(string='Invoice Number', required=True)
    OrderNumber = fields.Char(string='Order Number')
    Subtotal = fields.Float(string='Subtotal')
    Shipping = fields.Float(string='Shipping')
    CODCharge = fields.Float(string='COD Charge')
    CustomerNumber = fields.Char(string='Customer Number')
    DateInvoiced = fields.Date(string='Date Invoiced')
    InvoiceOriginalAmt = fields.Float(string='Invoice Original Amt')
    AddBalanceToCOD = fields.Float(string='Add Balance to COD')
    CODTotal = fields.Float(string='COD Total')
    UniqueId = fields.Integer(string='UniqueId')
    HandlingCharge = fields.Float(string='Handling Charge')
    Notes = fields.Text(string='Notes')
    Miscellaneous = fields.Float(string='Miscellaneous')
    InvoiceGrandTotal = fields.Float(string='Invoice Grand Total')
    DueDate = fields.Date(string='Due Date')
    DiscountDate = fields.Date(string='Discount Date')
    InvCommitted = fields.Boolean(string='Inv Committed')
    CommittedDateTime = fields.Datetime(string='Committed DateTime')
    InvoiceType = fields.Char(string='Invoice Type')
    DiscDays = fields.Integer(string='Disc Days')
    ShipDate = fields.Date(string='Ship Date')
    ShipMethod = fields.Char(string='Ship Method')
    PaidInFull = fields.Boolean(string='Paid In Full')
    PaidAmt = fields.Float(string='Paid Amt')
    CustInternalNumber = fields.Integer(string='Cust Internal Number')
    InvoiceParts = fields.One2many('legere.invoice.part', 'InvoiceId', string='Invoice Parts')

class LegereInvoicePart(models.Model):
    _name = "legere.invoice.part"
    _description = "Invoice Parts"

    InvoiceId = fields.Many2one('legere.invoice', string='Invoice Id', ondelete='cascade')
    InvoiceNumber = fields.Char(string='Invoice Number', required=True)
    ProductNumber = fields.Char(string='Product Number')
    Size = fields.Char(string='Size')
    Description = fields.Char(string='Description')
    UnitPrice = fields.Float(string='Unit Price')
    QtyOrdered = fields.Float(string='Qty Ordered')
    QtyShipped = fields.Float(string='Qty Shipped')
    Total = fields.Float(string='Total')
    UniqueId = fields.Integer(string='UniqueId')
    LotNumber = fields.Char(string='Lot Number')
    PrivateLabel = fields.Boolean(string='Private Label')
    Sample = fields.Boolean(string='Sample')
    PriceBreak = fields.Boolean(string='Price Break')
    NewProduct = fields.Boolean(string='New Product')
    SalespersonId = fields.Integer(string='SalespersonId')
    Territory = fields.Integer(string='Territory')
    PriceChanged = fields.Boolean(string='Price Changed')
    CommissionCode = fields.Integer(string='Commission Code')
    QtyBO = fields.Float(string='Qty BO')
    CustInternalNumber = fields.Integer(string='Cust Internal Number')
    ProductDescription = fields.Char(string='Product Description')
    ItemLineNumber = fields.Integer(string='Item Line Number')
    InvoiceUnitCost = fields.Float(string='Invoice Unit Cost')