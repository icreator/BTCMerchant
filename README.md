# Bitcoin and multy crypto-currency merchant for e-commerce

need Python 2.7
 

See Presentation of this Merchant by [ LITE.CASH service](https://docs.google.com/presentation/d/1y4zngsZVZ8L2fwQzsO8W0G2eQYAswKyjHawmcvAPEFQ/edit?usp=sharing/)

Основное отличие от других - не требует регистрации от магазина и плательщика

Оплата покупки покупателем может производиться в несколько платежей разными криптовалютами по курсу на внешних биржах. Например клиент купил товар и заказ оплатил частично биткоинами и частично лайткоинами. Если он сделал небольшую переплату то сдача ему возвращается или копится до следующего платежа если она очень маленькая

Так же есть возможность пополнения депозита клиента в магазине с накоплением - без покупок. Так чтобы клиент магазина мог потом оплатить покупку или даже передать свои средства другому клиенту магазина. Так

Сервер работает через RPC к кошелькам "полная нода" разных криптовалют

Курсы с бирж берутся автоматически через их API

Готовые модули для скриптов магазинов тут:
| Shop Script | Module  | Example |
|--|--|--|
| OpenCart | [Merchant Module](https://github.com/icreator/opencart_bitcoin_module) |[ Пример использования](https://opencartforum.com/files/file/2037-platezhi-v-bitkoin-na-sayt/)|
| Prestashop | [Merchant Module](https://github.com/icreator/prestashop_bitcoin_module) | |

