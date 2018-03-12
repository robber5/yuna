import datetime

try:
    import WindPy
except ImportError:
    pass

from ..core import SourceSingleton, Plane, Truck, SourceError


class WindpySource(SourceSingleton):

    @classmethod
    def call_to_source(cls):
        WindPy.w.start()

    def packing(self, stocks, dates):
        stocks_list = super().change_stock(stocks)
        from_query_date, to_query_date = self.__class__.datetime_to_date(self.__class__.validate_date(dates))
        plane = Plane()
        for stock_name in stocks_list:
            stock_data = self.__class__.wind_to_here(stock_name, from_query_date, to_query_date)
            plane.append(self.__class__.list_to_truck(stock_name, stock_data))
        return plane

    @classmethod
    def datetime_to_date(cls, validity_dates):
        return [i.strftime('%Y-%m-%d') for i in validity_dates]

    @classmethod
    def wind_to_here(cls, stock_name, from_query_date, to_query_date):
        return WindPy.w.wsd(stock_name, "low,high,close,volume,val_pe_deducted_ttm,pb_lf,ps_ttm,pcf_ncf_ttm",
                            from_query_date, to_query_date, "Fill=Previous;PriceAdj=F")

    @classmethod
    def list_to_truck(cls, stock_name, stock_data):
        truck = Truck()
        truck.extend('Code', [stock_name])
        truck.extend('Times', stock_data.Times)
        truck.extend('Low', stock_data.Data[0])
        truck.extend('High', stock_data.Data[1])
        truck.extend('Close', stock_data.Data[2])
        truck.extend('Volume', stock_data.Data[3])
        truck.extend('PE', [stock_data.Data[4][-1]])
        truck.extend('PB', [stock_data.Data[5][-1]])
        truck.extend('PS', [stock_data.Data[6][-1]])
        truck.extend('PCF', [stock_data.Data[7][-1]])
        return truck
