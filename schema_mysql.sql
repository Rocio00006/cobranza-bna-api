-- Esquema MySQL 8 del modulo Cobranza (7 tablas). La API lo crea sola al iniciar; este archivo es opcional.
CREATE DATABASE IF NOT EXISTS cobranza_bna CHARACTER SET utf8mb4;
USE cobranza_bna;

CREATE TABLE IF NOT EXISTS CREDITO (
        codCredito VARCHAR(20) NOT NULL PRIMARY KEY,
        idCliente VARCHAR(20) NOT NULL,
        idSolicitud VARCHAR(20) NOT NULL,
        montoAprobado DECIMAL(14,2) NOT NULL CHECK (montoAprobado > 0),
        moneda CHAR(3) NOT NULL DEFAULT 'PEN' CHECK (moneda IN ('PEN','USD')),
        fechaDesembolso DATETIME NOT NULL,
        estadoCredito VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS CUOTA (
        idCuota VARCHAR(20) NOT NULL PRIMARY KEY,
        codCredito VARCHAR(20) NOT NULL,
        numeroCuota INT NOT NULL CHECK (numeroCuota > 0),
        fechaVencimiento DATE NOT NULL,
        montoCuota DECIMAL(14,2) NOT NULL CHECK (montoCuota > 0),
        saldoPendiente DECIMAL(14,2) NOT NULL CHECK (saldoPendiente >= 0),
        moraPendiente DECIMAL(14,2) NOT NULL DEFAULT 0.00 CHECK (moraPendiente >= 0),
        estadoCuota VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
        UNIQUE (codCredito, numeroCuota),
        FOREIGN KEY (codCredito) REFERENCES CREDITO(codCredito)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS CANAL_PAGO (
        idCanal VARCHAR(10) NOT NULL PRIMARY KEY,
        nombreCanal VARCHAR(50) NOT NULL UNIQUE,
        tipoIntegracion VARCHAR(30) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS PAGO (
        idPago VARCHAR(20) NOT NULL PRIMARY KEY,
        codCredito VARCHAR(20) NOT NULL,
        idCanal VARCHAR(10) NOT NULL,
        fechaHora DATETIME NOT NULL,
        montoPago DECIMAL(14,2) NOT NULL CHECK (montoPago > 0),
        montoMora DECIMAL(14,2) NOT NULL DEFAULT 0.00 CHECK (montoMora >= 0),
        montoCapital DECIMAL(14,2) NOT NULL DEFAULT 0.00 CHECK (montoCapital >= 0),
        referenciaTransaccion VARCHAR(40) NOT NULL UNIQUE,
        estadoConfirmacion VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
        FOREIGN KEY (codCredito) REFERENCES CREDITO(codCredito),
        FOREIGN KEY (idCanal) REFERENCES CANAL_PAGO(idCanal)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS APLICACION_PAGO (
        idAplicacion VARCHAR(20) NOT NULL PRIMARY KEY,
        idPago VARCHAR(20) NOT NULL,
        idCuota VARCHAR(20) NOT NULL,
        montoAplicado DECIMAL(14,2) NOT NULL CHECK (montoAplicado > 0),
        FOREIGN KEY (idPago) REFERENCES PAGO(idPago),
        FOREIGN KEY (idCuota) REFERENCES CUOTA(idCuota)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS MORA (
        idMora VARCHAR(20) NOT NULL PRIMARY KEY,
        idCuota VARCHAR(20) NOT NULL,
        diasAtraso INT NOT NULL CHECK (diasAtraso >= 0),
        montoCalculado DECIMAL(14,2) NOT NULL CHECK (montoCalculado >= 0),
        fechaCalculo DATETIME NOT NULL,
        vigente BOOLEAN NOT NULL DEFAULT TRUE,
        FOREIGN KEY (idCuota) REFERENCES CUOTA(idCuota)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS EVENTO_AUDITORIA (
        idEvento VARCHAR(20) NOT NULL PRIMARY KEY,
        idEntidad VARCHAR(20) NOT NULL,
        tipoEvento VARCHAR(30) NOT NULL,
        `timestamp` DATETIME NOT NULL,
        moduloEmisor VARCHAR(30) NOT NULL,
        usuarioOperador VARCHAR(30) NOT NULL,
        resultado VARCHAR(20) NOT NULL DEFAULT 'EXITOSO'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO CANAL_PAGO (idCanal, nombreCanal, tipoIntegracion) VALUES ('HB', 'Home Banking', 'API REST via Bus de Servicios');
