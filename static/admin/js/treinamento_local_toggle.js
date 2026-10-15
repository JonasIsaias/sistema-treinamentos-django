// static/admin/js/treinamento_local_toggle.js
(function($) {
    $(document).ready(function() {
        var localField = $('#id_local');
        // Acessa a 'row' (linha) do form para mostrar/esconder o campo e seu label
        var localPersonalizadoRow = $('#id_local_personalizado').closest('.form-row, .form-group');

        function toggleLocalPersonalizado() {
            if (localField.val() === 'outro') {
                localPersonalizadoRow.show();
                // Adiciona um asterisco ao label para indicar que é obrigatório (visual)
                localPersonalizadoRow.find('label').addClass('required');
            } else {
                localPersonalizadoRow.hide();
                $('#id_local_personalizado').val(''); // Limpa o valor ao esconder
                localPersonalizadoRow.find('label').removeClass('required');
            }
        }

        // Executa a função quando a página carregar
        toggleLocalPersonalizado();

        // Executa a função toda vez que o campo 'local' mudar
        localField.change(toggleLocalPersonalizado);
    });
})(django.jQuery);