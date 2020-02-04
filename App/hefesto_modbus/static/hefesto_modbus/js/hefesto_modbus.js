django.jQuery(function ($) {
    'use strict';
    // select private_key/certificate field text on click
    var conexion = $('.field-tipo_conexion select')
    var function_ = $('.field-codigo_funcion select')
    var reloadConexion = function () {
        var conexionSerial = $('.conexion_serial')
        var conexionTCP = $('.conexion_tcp')
        var value = $('.field-tipo_conexion select').val();
        console.log("value: ", value)
        if (value == "RTU/SERIAL") {
            conexionSerial.show();
            conexionTCP.hide();
        } else {
            conexionSerial.hide();
            conexionTCP.show();
        }
    }
    var reloadInlines = function () {
        var lecturaInline = $('#variablelectura_set-group')
        var escrituraInline = $('#variableescritura_set-group')
        var value = $('.field-codigo_funcion select').val();
        console.log("value: ", value)
        if (value == 3 || value == 4) {
            lecturaInline.show();
            escrituraInline.hide();
        } else {
            lecturaInline.hide();
            escrituraInline.show();
        }
    };
    conexion.on('change', function (e) {
        reloadConexion();
    });
    function_.on('change', function (e) {
        reloadInlines();
    });
    reloadConexion();
    reloadInlines();
    console.log("modbus_hefesto loaded");
});
