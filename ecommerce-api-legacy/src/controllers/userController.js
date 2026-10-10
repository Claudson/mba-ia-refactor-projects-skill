// Texto mantido por compatibilidade com o contrato original da API.
const USER_DELETED_MESSAGE = 'Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.';

function createUserController({ userModel }) {
    return Object.freeze({
        async deleteUser(id) {
            await userModel.deleteById(id);
            return USER_DELETED_MESSAGE;
        },
    });
}

module.exports = { createUserController };
