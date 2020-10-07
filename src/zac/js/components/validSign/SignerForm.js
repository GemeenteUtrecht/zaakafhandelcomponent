import React, { useContext, useState } from 'react';
import PropTypes from 'prop-types';
import camelCaseKeys from 'camelcase-keys';

import { getUserName } from '../../utils/users';
import { TextInput, HiddenInput } from '../forms/Inputs';
import {ErrorList, extractErrors, getAttr, Wrapper, isEmpty} from '../forms/Utils';
import { UserSelection } from '../user-selection';









const SignerForm = ({ index, data: { values, errors } }) => {
    values = camelCaseKeys(values);

    const defaultSelectUser = (values && values.user) ? {
        id: parseInt(values.user, 10),
        firstName: values.first_name,
        lastName: values.last_name,
        email: values.email,
    } : null;

    const [selectedUser, setSelectedUser] = useState(defaultSelectUser);
    const hasUser = !isEmpty(selectedUser);

    const email = getAttr('email', [selectedUser, values]);
    const firstName = getAttr('firstName', [selectedUser, values]);
    const lastName = getAttr('lastName', [selectedUser, values]);

    return (
        <div className="validsign-signer">

            <div className="validsign-signer__index"># {index + 1}</div>

            { ( errors && !isEmpty(errors.__all__) )
                ? (
                    <Wrapper errors={ errors.__all__ }>
                        <ErrorList errors={ extractErrors(errors.__all__) } />
                    </Wrapper>
                ) : null
            }

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
                    initial={ email }
                    required={ false }
                    label="E-mailadres"
                    helpText="De ondertekenaar ontvangt op dit e-mailadres een uitnoding ter ondertekening."
                    errors={ extractErrors(getAttr('email', [errors], [])) }
                />
            </div>

            <div className="form__field-group">
                <TextInput
                    id="id_first_name"
                    name="first_name"
                    initial={ firstName }
                    required={ false }
                    label="Voornaam"
                    helpText="De voornaam van de ondertekenaar."
                    errors={ extractErrors(getAttr('first_name', [errors], [])) }
                />

                <TextInput
                    id="id_last_name"
                    name="last_name"
                    initial={ lastName }
                    required={ false }
                    label="Achternaam"
                    helpText="De achternaam van de ondertekenaar."
                    errors={ extractErrors(getAttr('last_name', [errors], [])) }
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
