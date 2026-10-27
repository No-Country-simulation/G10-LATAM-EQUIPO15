# Tokenización de tarjetas en pagos digitales

## Qué es la tokenización
La tokenización reemplaza el número de tarjeta (PAN) por un valor sustituto llamado token, que no tiene valor fuera del sistema que lo emitió. El comercio guarda el token y nunca almacena el número real. Si una base de datos del comercio se filtra, los tokens no permiten realizar compras en otros sitios.

## Bóveda de tokens
El emisor del token mantiene una bóveda: una base de datos protegida que relaciona cada token con su PAN. Solo la bóveda puede revertir el token al número original, operación llamada detokenización. El acceso a la bóveda se restringe a servicios autorizados y cada consulta queda registrada para auditoría.

## Tokens de red y tokens de comercio
Los tokens de red los emiten las marcas de tarjeta y se vinculan a un dispositivo o a un comercio concreto. Se actualizan automáticamente cuando la tarjeta física se renueva, lo que reduce los rechazos por tarjeta vencida en pagos recurrentes. Los tokens de comercio los genera un proveedor de pagos y solo son válidos dentro de su plataforma.

## Relación con PCI DSS
El estándar PCI DSS define los requisitos de seguridad para quienes almacenan, procesan o transmiten datos de tarjetas. Al no guardar el PAN, el comercio reduce el alcance de los sistemas sujetos a auditoría PCI DSS, aunque no queda exento de cumplir los controles sobre los sistemas que sí reciben datos de tarjeta.

## Diferencia con el cifrado
El cifrado transforma el PAN con una clave y es reversible por quien tenga esa clave. La tokenización no deriva el token del número mediante una fórmula: la relación existe solo en la bóveda. Por eso, robar el token no permite reconstruir el número aunque se conozca el algoritmo.
