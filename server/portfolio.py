#!flask/bin/python

"""Alternative version of the ToDo RESTful server implemented using the
Flask-RESTful extension."""

from flask import Flask, jsonify, abort, make_response
from flask.ext.restful import Api, Resource, reqparse, fields, marshal
from flask.ext.httpauth import HTTPBasicAuth
import json
from pprint import pprint

app = Flask(__name__, static_url_path="")
api = Api(app)
auth = HTTPBasicAuth()


@auth.get_password
def get_password(username):
    if username == 'dtogni':
        return 'dt1234'
    return None


@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default
    # auth dialog
    return make_response(jsonify({'message': 'Unauthorized access'}), 403)

# load file in memory
with open('portfolio.json') as data_file:    
    portfolio = json.load(data_file)

pprint(portfolio)

ticker_fields = {
    'symbol': fields.String,
    'amount': fields.Float,
    'cost': fields.Float
}


class PortfolioAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('symbol', type=str, required=True,
                                   help='No symbol title provided',
                                   location='json')
        self.reqparse.add_argument('amount', type=float, default=0.0,
                                   location='json')
        super(PortfolioAPI, self).__init__()

    def get(self):
        return {'tickers': [marshal(ticker, ticker_fields) for ticker in portfolio]}

    def post(self):
        args = self.reqparse.parse_args()
        ticker = {
            'symbol': args['symbol'],
            'amount': args['amount'],
            'cost': args['cost']
        }
        portfolio.append(task)
        return {'ticker': marshal(ticker, ticker_fields)}, 201


class TickerAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('symbol', type=str, location='json')
        self.reqparse.add_argument('amount', type=float, location='json')
        self.reqparse.add_argument('cost', type=float, location='json')
        super(TickerAPI, self).__init__()

    def get(self, symbol):
        ticker = [ticker for ticker in portfolio if ticker['symbol'] == symbol]
        if len(ticker) == 0:
            abort(404)
        return {'ticker': marshal(ticker[0], ticker_fields)}

    def put(self, symbol):
        ticker = [ticker for ticker in portfolio if ticker['symbol'] == symbol]
        if len(ticker) == 0:
            abort(404)
        ticker = ticker[0]
        args = self.reqparse.parse_args()
        for k, v in args.items():
            if v is not None:
                task[k] = v
        return {'ticker': marshal(ticker, ticker_fields)}

    def delete(self, symbol):
        ticker = [ticker for ticker in portfolio if ticker['symbol'] == symbol]
        if len(ticker) == 0:
            abort(404)
        ticker.remove(ticker[0])
        return {'result': True}


api.add_resource(PortfolioAPI, '/todo/api/v1.0/portfolio', endpoint='portfolio')
api.add_resource(TickerAPI, '/todo/api/v1.0/ticker/<string:symbol>', endpoint='ticker')


if __name__ == '__main__':
    app.run(debug=True)
