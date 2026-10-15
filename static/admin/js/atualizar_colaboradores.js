document.addEventListener('DOMContentLoaded', function () {
    const campoMatriculas = document.querySelector('#id_matriculas');
    const campoColaboradores = document.querySelector('#id_colaboradores');

    if (!campoMatriculas || !campoColaboradores) return;

    function buscarColaboradores(matriculas) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        fetch('/admin/core/treinamento/atualizar_colaboradores_por_matriculas/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken,
            },
            body: new URLSearchParams({ matriculas: matriculas })
        })
        .then(response => response.json())
        .then(data => {
            if (data.html) {
                campoColaboradores.innerHTML = data.html;
            } else {
                campoColaboradores.innerHTML = '<option>Nenhum colaborador encontrado</option>';
            }
        })
        .catch(error => {
            console.error('Erro ao buscar colaboradores:', error);
            campoColaboradores.innerHTML = '<option>Erro ao buscar colaboradores</option>';
        });
    }

    campoMatriculas.addEventListener('input', function () {
        const texto = campoMatriculas.value.trim();
        if (texto.length > 0) {
            buscarColaboradores(texto);
        }
    });
});