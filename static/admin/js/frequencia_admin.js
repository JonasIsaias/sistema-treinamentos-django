document.addEventListener('DOMContentLoaded', function () {
    function toggleJustificativaCampos(presenteCheckbox) {
        const row = presenteCheckbox.closest('.form-row') || presenteCheckbox.closest('div');
        const justificativaField = row.querySelector('[id$="-justificativa"]').closest('.form-row') || row.querySelector('[id$="-justificativa"]').closest('div');
        const anexoField = row.querySelector('[id$="-anexo"]').closest('.form-row') || row.querySelector('[id$="-anexo"]').closest('div');

        if (presenteCheckbox.checked) {
            if (justificativaField) justificativaField.style.display = 'none';
            if (anexoField) anexoField.style.display = 'none';
        } else {
            if (justificativaField) justificativaField.style.display = '';
            if (anexoField) anexoField.style.display = '';
        }
    }

    // Aplica a lógica para cada linha de formulário
    document.querySelectorAll('input[type=checkbox][id$="-presente"]').forEach(function (checkbox) {
        toggleJustificativaCampos(checkbox);
        checkbox.addEventListener('change', function () {
            toggleJustificativaCampos(this);
        });
    });
});