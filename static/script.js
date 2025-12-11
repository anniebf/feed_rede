document.addEventListener('DOMContentLoaded', function() {
    // Controle dos tipos de postagem
    const typeButtons = document.querySelectorAll('.type-btn');
    const postTypeInput = document.getElementById('post-type');
    const mediaUpload = document.getElementById('media-upload');
    const mediaInput = document.getElementById('media');
    const contentTextarea = document.getElementById('content');

    if (typeButtons.length > 0) {
        typeButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove a classe active de todos os botões
                typeButtons.forEach(btn => btn.classList.remove('active'));

                // Adiciona a classe active ao botão clicado
                this.classList.add('active');

                // Atualiza o tipo de postagem
                const type = this.getAttribute('data-type');
                postTypeInput.value = type;

                // Mostra ou esconde o campo de upload de mídia
                if (type === 'text') {
                    mediaUpload.style.display = 'none';
                    mediaInput.removeAttribute('required');
                    contentTextarea.setAttribute('placeholder', 'O que você está pensando?');
                } else {
                    mediaUpload.style.display = 'block';
                    mediaInput.setAttribute('required', 'required');

                    if (type === 'image') {
                        mediaInput.setAttribute('accept', 'image/*');
                        contentTextarea.setAttribute('placeholder', 'Descrição da imagem...');
                    } else if (type === 'video') {
                        mediaInput.setAttribute('accept', 'video/*');
                        contentTextarea.setAttribute('placeholder', 'Descrição do vídeo...');
                    }
                }
            });
        });
    }

    // Popup de informações do usuário
    const userAvatars = document.querySelectorAll('.user-avatar');
    const userPopup = document.getElementById('user-popup');
    let popupTimeout;

    userAvatars.forEach(avatar => {
        avatar.addEventListener('mouseenter', function(e) {
            clearTimeout(popupTimeout);

            const userId = this.getAttribute('data-user-id');
            if (!userId) return;

            // Busca informações do usuário
            fetch(`/get_user_info/${userId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error(data.error);
                        return;
                    }

                    // Posiciona e mostra o popup
                    const rect = this.getBoundingClientRect();
                    userPopup.style.left = `${rect.left}px`;
                    userPopup.style.top = `${rect.bottom + 10}px`;

                    // Conteúdo do popup
                    userPopup.innerHTML = `
                        <div class="user-popup-header">
                            <img src="${data.profile_pic}" alt="${data.username}">
                            <h4>${data.username}</h4>
                        </div>
                        <div class="user-popup-bio">
                            <p>${data.bio || 'Nenhuma descrição fornecida.'}</p>
                        </div>
                    `;

                    userPopup.classList.add('active');
                })
                .catch(error => {
                    console.error('Erro ao buscar informações do usuário:', error);
                });
        });

        avatar.addEventListener('mouseleave', function() {
            popupTimeout = setTimeout(() => {
                userPopup.classList.remove('active');
            }, 300);
        });
    });

    // Impede que o popup feche quando o mouse estiver sobre ele
    userPopup.addEventListener('mouseenter', function() {
        clearTimeout(popupTimeout);
    });

    userPopup.addEventListener('mouseleave', function() {
        this.classList.remove('active');
    });

    // Para dispositivos touch
    userAvatars.forEach(avatar => {
        avatar.addEventListener('touchstart', function(e) {
            e.preventDefault();
            this.dispatchEvent(new Event('mouseenter'));
        });

        avatar.addEventListener('touchend', function(e) {
            e.preventDefault();
            setTimeout(() => {
                userPopup.classList.remove('active');
            }, 2000);
        });
    });

    // Validação do formulário de postagem
    const postForm = document.getElementById('post-form');
    if (postForm) {
        postForm.addEventListener('submit', function(e) {
            const postType = postTypeInput.value;
            const content = contentTextarea.value.trim();

            if (postType === 'text' && content === '') {
                e.preventDefault();
                alert('Por favor, digite algum conteúdo para sua postagem de texto.');
                contentTextarea.focus();
                return;
            }

            if ((postType === 'image' || postType === 'video') && mediaInput.files.length === 0) {
                e.preventDefault();
                alert(`Por favor, selecione um arquivo para sua postagem de ${postType === 'image' ? 'imagem' : 'vídeo'}.`);
                return;
            }
        });
    }
});