document.addEventListener('DOMContentLoaded', function() {
    // --- Variáveis Comuns ---
    const userPopup = document.getElementById('user-popup');
    let popupTimeout;

    // --- 1. Controle dos Tipos de Postagem (Mantido) ---
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
                this.classList.add('active');

                const type = this.getAttribute('data-type');
                postTypeInput.value = type;

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

    // --- 2. Lógica de Upload da Foto de Perfil (NOVA LÓGICA) ---
    const myPicContainer = document.querySelector('.my-profile-pic-container');
    const fileInput = document.getElementById('profile-pic-input');
    const profilePicImg = document.getElementById('my-profile-pic');

    if (myPicContainer && fileInput && profilePicImg) {
        // A) Ao clicar no avatar logado, abre o seletor de arquivo
        myPicContainer.addEventListener('click', function() {
            fileInput.click();
        });

        // B) Ao selecionar o arquivo, envia o formulário via Fetch API
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                // Prepara os dados para o envio
                const formData = new FormData();
                // O nome 'profile_pic_file' deve corresponder ao que é esperado no app.py
                formData.append('profile_pic_file', fileInput.files[0]);

                // Exibe uma mensagem de carregamento ou desabilita o clique, se necessário
                myPicContainer.style.cursor = 'wait';

                // Envio assíncrono para o backend
                fetch('{{ url_for("upload_profile_pic") }}', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    myPicContainer.style.cursor = 'pointer'; // Retorna o cursor normal
                    // Verifica se a resposta HTTP é OK (status 200)
                    if (!response.ok) {
                        return response.json().then(err => { throw new Error(err.message || 'Erro no servidor.'); });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        // Atualiza a imagem no DOM
                        profilePicImg.src = data.new_pic_url;
                        alert(data.message);
                    } else {
                        alert('Erro ao atualizar foto: ' + data.message);
                    }
                })
                .catch(error => {
                    myPicContainer.style.cursor = 'pointer';
                    console.error('Erro de upload:', error);
                    alert(`Falha no upload: ${error.message}`);
                });
            }
        });
    }

    // --- 3. Popup de Informações do Usuário (Modificado para excluir o usuário logado) ---
    const userAvatars = document.querySelectorAll('.user-avatar');

    userAvatars.forEach(avatar => {
        // Verifica se é o avatar do usuário logado (se contém a classe my-profile-pic-container)
        const isMyAvatar = avatar.classList.contains('my-profile-pic-container');

        // Se for o seu avatar, a lógica de popup é ignorada em favor da lógica de upload (ponto 2)
        if (isMyAvatar) {
            // A lógica de hover para o seu avatar é puramente CSS
            return;
        }

        // Lógica de Popup para OUTROS avatares
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
                    // Ajuste o posicionamento aqui, se necessário
                    userPopup.style.left = `${rect.left + rect.width / 2}px`; // Centraliza
                    userPopup.style.top = `${rect.bottom + 10}px`;
                    userPopup.style.transform = 'translateX(-50%)'; // Centraliza

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

        // Para dispositivos touch (Mantenha o touchend mais longo para visualização)
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

    // Impede que o popup feche quando o mouse estiver sobre ele (Mantido)
    userPopup.addEventListener('mouseenter', function() {
        clearTimeout(popupTimeout);
    });

    userPopup.addEventListener('mouseleave', function() {
        this.classList.remove('active');
    });


    // --- 4. Validação do formulário de postagem (Mantido) ---
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