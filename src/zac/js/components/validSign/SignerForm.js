import React, { useContext, useState } from 'react';
import PropTypes from 'prop-types';

import { getUserName } from '../../utils/users';
import { TextInput, HiddenInput } from '../forms/Inputs';
import { UserSelection } from '../user-selection';


const SignerForm = ({ index, data }) => {
    const [selectedUser, setSelectedUser] = useState(null);
    const hasUser = Boolean(selectedUser && Object.keys(selectedUser).length);

    return (
        <div className="validsign-signer">

            <div className="validsign-signer__index"># {index + 1}</div>

            <div className="form__field-group">
                <div className="validsign-signer__select-user">
                    <HiddenInput name="user" initial={ hasUser ? selectedUser.id : '' } />

                    { hasUser ? <div>{ getUserName(selectedUser) }</div> : null }

                    <UserSelection
                        onSelection={ setSelectedUser }
                        asLink={ hasUser }
                        btnLabel={ hasUser ? 'Wijzig' : 'Selecteer gebruiker' }
                    />
                </div>

                <TextInput
                    type="email"
                    id="id_email"
                    name="email"
                    initial={ selectedUser ? (selectedUser.email || '') : '' }
                    required={ false }
                    label="E-mailadres"
                    helpText="De ondertekenaar ontvangt op dit e-mailadres een uitnoding ter ondertekening."
                    errors={ [] }
                />
            </div>

            <div className="form__field-group">
                <TextInput
                    id="id_first_name"
                    name="first_name"
                    initial={ selectedUser ? (selectedUser.firstName || '') : '' }
                    required={ false }
                    label="Voornaam"
                    helpText="De voornaam van de ondertekenaar."
                    errors={ [] }
                />

                <TextInput
                    id="id_last_name"
                    name="last_name"
                    initial={ selectedUser ? (selectedUser.lastName || '') : '' }
                    required={ false }
                    label="Achternaam"
                    helpText="De achternaam van de ondertekenaar."
                    errors={ [] }
                />
            </div>

        </div>
    );
};

SignerForm.propTypes = {
    index: PropTypes.number.isRequired,
    data: PropTypes.object.isRequired,
};


export { SignerForm };
