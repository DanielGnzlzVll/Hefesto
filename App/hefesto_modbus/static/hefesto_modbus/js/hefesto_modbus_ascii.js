django.jQuery(function ($) {
    'use strict';
    $(document).on('formset:added', function(event, $row, formsetName) {
        if (formsetName == 'variablelectura_set') {
            reloadColumns()
        }
    });
    $(document).on('formset:removed', function(event, $row, formsetName) {
        if (formsetName == 'variablelectura_set') {
            reloadColumns()
        }
    });
    $(document).on('change', function(event) {
        let parent_class = event.target.parentElement.className;

        if (parent_class === "field-tipo_dato"){
            reloadColumns()
        }
    });
    
    let hideHeader = (value) => {
        let header = $('#variablelectura_set-group')[0].querySelectorAll('.column-longitud_texto')[0]
        header.hidden = value
    }

    let count_ascii = () => {
        var count = 0
        let selected = $('#variablelectura_set-group')[0].querySelectorAll("tr.dynamic-variablelectura_set > td.field-tipo_dato > select")
        selected.forEach((item)=> {
            if (item.value == "s"){
                count = count + 1
            }
        })
        return count;
    }

    let hideColumns = (value) => {
        let selected = $('#variablelectura_set-group')[0].querySelectorAll("tr.dynamic-variablelectura_set > td.field-longitud_texto")
        selected.forEach((item)=> {
            item.hidden = value
        })
    }

    let enableColumns = () => {
        let selected = $('#variablelectura_set-group')[0].querySelectorAll("tr.dynamic-variablelectura_set")
        selected.forEach((item)=> {
            let tipo_dato = item.querySelector(".field-tipo_dato > select").value
            let disable = tipo_dato !== "s"
            
            let longitud_texto = item.querySelector(".field-longitud_texto > input")
            if (disable){
                longitud_texto.value = "1"
            }
            longitud_texto.disabled = disable
        })
    }

    let reloadColumns = () => {

        let count_columns = count_ascii()
        enableColumns()
        if( count_columns == 0 ){
            hideHeader(true)
            hideColumns(true)
        }else{
            hideHeader(false)
            hideColumns(false)
        }

    }
    reloadColumns()

});
