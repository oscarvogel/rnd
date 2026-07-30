# -*- coding: utf-8 -*-
import logging

import decimal

from libs import Ventanas
from modelos.CostoFijoPorProducto import Cfijoxprod
from modelos.CostosFijos import Cfijo
from modelos.CuotasPago import Cuotaspago
from modelos.FletePorKG import Fporkg
from modelos.FletePorcentaje import Fporcien
from modelos.FletesPorBulto import Fpbulto
from modelos.FormasDePago import FormaPago
from modelos.Impuestos import Impuesto
from modelos.Stock import Stock

IVA21 = 21.00
IVA105 = 10.5
IVAID21 = 5

class Fiscal(object):

    ticket = True #si imprime en tickeadora o factura
    nTotFact = 0.00 #monto total de la factura
    lista = '1' #lista del cliente
    contado = True #indica si la factura es de contado

    def ImprimeTicket(self):

        if (self.nTotFact < 10000 and self.lista == '1' and self.contado):
            self.ticket = True
        elif not self.contado:
            self.ticket = False
        else:
            self.ticket = False

        logging.info("Ticket {} contado {} lista {} total fact{} "
                     .format(self.ticket, self.contado, self.lista, self.nTotFact))
        return self.ticket

def MargenReverso(minimo=0.00, descuento=0.00, redondeo=4):
    if isinstance(minimo, (decimal.Decimal,)):
        minimo = float(minimo)
    if isinstance(descuento, (decimal.Decimal,)):
        descuento = float(descuento)
    item = minimo
    x = (item + descuento) / (1-(descuento/100.))
    return round(x, redondeo)

def Margen(margen=0.00, descuento=0.00, redondeo=4):
    if isinstance(descuento, (decimal.Decimal,)): #en caso de que sea decimal lo convierto a float
        descuento = float(descuento)
    if isinstance(margen, (decimal.Decimal,)): #en caso de que sea decimal lo convierto a float
        margen = float(margen)

    x = (margen) - (margen + 100.) * descuento / 100.
    return round(x, redondeo)


class Calculaprecio(object):

    fijo = decimal.Decimal.from_float(0.)

    def PrecioBase(self, nPrecio = 0.00, lReparto = False, clave = '', cLista = '1'):
        if isinstance(nPrecio, (float,)):
            nPrecio = decimal.Decimal.from_float(nPrecio)
        nRetorno = decimal.Decimal.from_float(0.0)
        stock = Stock.get_by_id(clave)
        flete = decimal.Decimal.from_float(0.)
        if stock:
            if nPrecio == 0.0:
                nPrecio = stock.preciopro
            if eval('stock.incre' + cLista) <= 0:
                Ventanas.showAlert("Sistema", "El articulo {} no tiene establecido un margen y no podemos continuar".
                                   format(clave))
            else:
                if stock.clave[7:].strip() != '':
                    nPrecio = eval(str(nPrecio) + stock.formu.strip())
                    if isinstance(nPrecio, (float,)):
                        nPrecio = decimal.Decimal.from_float(nPrecio)
                    flete = self.PrecioFlete(stock, cLista, nPrecio)
                    cfijo = self.CostoFijo(stock, nPrecio)
                else:
                    flete = self.PrecioFlete(stock, cLista, nPrecio)
                    cfijo = self.CostoFijo(stock, nPrecio)
                nRetorno = flete + cfijo
                nRetorno += nPrecio + nPrecio * eval('stock.incre' + cLista) / 100
                nRetorno += nRetorno * self.DevImp(stock.tipoimp) / 100

        return nRetorno

    def DevImp(self, tipoimp='01'):
        nRetorno = Impuesto.get_by_id(tipoimp).porcentaje
        return nRetorno

    def PrecioFlete(self, stock, cLista, nPrecio):
        if isinstance(nPrecio, (float,)):
            nPrecio = decimal.Decimal.from_float(nPrecio)
        flete = decimal.Decimal.from_float(0.0)
        if stock['FPORCEN'].strip() != '':
            fporcien = Fporcien.get_by_id(stock.fporcen)
            flete = nPrecio * eval('fporcien.porcentaje' + cLista) / 100
        elif stock['FMULTI'].strip() != '':
            fmulti = Fporkg.get_by_id(stock.fmulti)
            flete = eval('fmulti.precio' + cLista) * float(stock.peso)
        elif stock['FSUMA'].strip() != '':
            fmulti = Fporkg.get_by_id(stock.fsuma)
            flete = eval('fmulti.precio' + cLista)
        elif stock['FPBULTO'].strip() != '':
            fpbulto = Fpbulto.get_by_id(stock.fpbulto)
            flete = fpbulto.precio

        return flete

    def CostoFijo(self, stock, nPrecio):
        nFijo = decimal.Decimal.from_float(0.)
        cfxp = Cfijoxprod.select().where(Cfijoxprod.id_art_x_med == stock.id_art_x_med)
        for c in cfxp:
            nFijo += self.DevCFijo(c.c_fijo, False, nPrecio)

        self.fijo = nFijo
        return nFijo

    def DevCFijo(self, cFijo, reparto=False, nPrecio=0.0):
        if isinstance(nPrecio, (float,)):
            nPrecio = decimal.Decimal.from_float(nPrecio)
        cfijo = Cfijo.get_by_id(cFijo)
        nRetorno = decimal.Decimal.from_float(0.0)
        if reparto:
            if cfijo.reparto:
                nRetorno = cfijo.costo + (nPrecio * cfijo.porcentaje / 100)
        else:
            if cfijo.retira:
                nRetorno = cfijo.costo + (nPrecio * cfijo.porcentaje / 100)

        return nRetorno

    def PrecioPublico(self, nPrecio = 0, pago = '', cuotapago = 0, cLista = '1', articulo=''):
        nRecargo = decimal.Decimal.from_float(0.0)
        nDescuento = decimal.Decimal.from_float(0.0)
        nRetorno = decimal.Decimal.from_float(0.0)
        if isinstance(nPrecio, (float,)):
            nPrecio = decimal.Decimal.from_float(nPrecio)

        formapago = FormaPago.get_by_id(pago)

        if formapago.categoria == '02': #si es tarjeta de credito busco la cuota
            cuota = Cuotaspago.get_by_id(cuotapago)
            if cLista == '1':
                nRecargo = cuota.recargo
                nDescuento = cuota.bonificacion
            else:
                nRecargo = cuota.recargol4
                nDescuento = cuota.bonificacionl4
        else:
            nDescuento = formapago.des1
            nRecargo = formapago.punitorio

        nRetorno = nPrecio + nPrecio * nRecargo / 100 - nPrecio * nDescuento / 100
        nIVA = Stock().PorcentajeIVA(clave=articulo)
        nRetorno += nRetorno * nIVA / 100
        return nRetorno