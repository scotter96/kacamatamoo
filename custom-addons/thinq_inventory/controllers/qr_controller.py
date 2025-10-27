import base64
import io
from odoo import http
from odoo.http import request

try:
    import qrcode
    from qrcode.image.pil import PilImage
except ImportError:
    qrcode = None

class QRController(http.Controller):

    # dipanggil via /thinq_inventory/qr?picking_id=ID_PICKING di shipping label_template.xml
    @http.route('/thinq_inventory/qr', type='http', auth='public', methods=['GET'])
    def generate_qr(self, **kwargs):
        """Generate QR code untuk shipping label"""
        
        if not qrcode:
            # Fallback jika qrcode library tidak tersedia
            return request.not_found()
        
        # Ambil parameter
        picking_id = kwargs.get('picking_id')
        
        if not picking_id:
            return request.not_found()
        
        try:
            # Ambil data picking
            picking = request.env['stock.picking'].sudo().browse(int(picking_id))
            if not picking.exists():
                return request.not_found()
            
            # Generate URL untuk QR code (bukan data langsung)
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            qr_url = f"{base_url}/thinq_inventory/shipment/{picking.id}" # URL untuk membuat info shipment
            
            # Generate QR Code dengan URL
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            
            # Return image response
            return request.make_response(
                img_data,
                headers=[
                    ('Content-Type', 'image/png'),
                    ('Content-Length', len(img_data)),
                    ('Cache-Control', 'no-cache'),
                ]
            )
            
        except Exception as e:
            return request.not_found()

    # dipanggil dari generate_qr - menampilkan info shipment via website
    @http.route('/thinq_inventory/shipment/<int:picking_id>', type='http', auth='public', methods=['GET'], website=True)
    def display_shipment_info(self, picking_id, **kwargs):
        """Display shipment information when QR is scanned"""
        
        try:
            # Ambil data picking
            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return request.not_found()
            
            # Prepare data untuk template
            shipment_data = self._prepare_shipment_display_data(picking)
            
            # Render template
            return request.render('thinq_inventory.shipment_info_template', {
                'picking': picking,
                'shipment_data': shipment_data
            })
            
        except Exception as e:
            return request.not_found()
    
    def _prepare_shipment_display_data(self, picking):
        """Prepare data untuk display di halaman shipment info"""
        
        if picking.picking_type_code == 'outgoing': # Outgoing = Delivery (SO)
            # Delivery: Data pengirim = company
            shipment_data = {
                'type': 'Delivery',
                'doc_no': picking.name,
                'sender_name': picking.location_id.company_id.name or picking.company_id.name,
                'sender_address': picking.location_id.company_id.street or picking.company_id.street,
                'sender_city': picking.location_id.company_id.city or picking.company_id.city,
                'sender_phone': picking.location_id.company_id.phone or picking.company_id.phone,
                'recipient_name': picking.partner_id.name,
                'recipient_address': picking.partner_id.street,
                'recipient_city': picking.partner_id.city,
                'recipient_phone': picking.partner_id.phone,
            }
        else: # Incoming = Receipt (PO) - Data pengirim = partner
            shipment_data = {
                'type': 'Receipt',
                'doc_no': picking.name,
                'sender_name': picking.partner_id.name,
                'sender_address': picking.partner_id.street,
                'sender_city': picking.partner_id.city,
                'sender_phone': picking.partner_id.phone,
                'recipient_name': picking.company_id.name,
                'recipient_address': picking.company_id.street,
                'recipient_city': picking.company_id.city,
                'recipient_phone': picking.company_id.phone,
            }
        
        return shipment_data