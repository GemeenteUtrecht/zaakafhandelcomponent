import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { getUserName } from '../../utils/users';
import { HiddenInput } from '../forms/Inputs';
import { ErrorList, Wrapper } from '../forms/Utils';

const setUsers = (users) => (users ? users.map((user) => ({
    value: user.id,
    label: getUserName(user),
})) : null);

const isEmpty = (obj) => {
    if (!obj) {
        return true;
    }
    return Object.keys(obj).length === 0;
};

const extractErrors = (errList) => errList.map((err) => err.msg);

const UserSelectForm = ({ index, data: { values, errors }, users }) => {
    const [selectedData, setSelectedData] = useState(null);
    const [hiddenInputs, setHiddenInputs] = useState(null);

    // Default hidden input for the form
    const DefaultHiddenInput = () => (
        <input type="hidden" name={`kownsl_users${-index}`} required="required" />
    );

    // Create hidden inputs of the selected users
    const getHiddenInputs = (selectedUsers) => {
        const inputs = selectedUsers ? selectedUsers.map((user) => <HiddenInput name="kownsl_users" value={user.value} />) : DefaultHiddenInput;
        setHiddenInputs(inputs);
    };

    useEffect(() => {
        getHiddenInputs(selectedData);
    }, [selectedData]);

    const handleSelectChange = (value) => {
        setSelectedData(value);
    };

    return (
        <>
            { (errors && !isEmpty(errors.__all__))
                ? (
                    <Wrapper errors={errors.__all__}>
                        <ErrorList errors={extractErrors(errors.__all__)} />
                    </Wrapper>
                ) : null}

            <h1>{`Stap ${index + 1}`}</h1>
            {hiddenInputs}
            <Select
                isMulti
                cacheOptions
                placeholder="Selecteer adviseur(s)"
                name={`kownsl_users${-index}`}
                options={setUsers(users)}
                className="basic-multi-select"
                classNamePrefix="select"
                onChange={(value) => handleSelectChange(value)}
            />
        </>
    );
};

UserSelectForm.propTypes = {
    index: PropTypes.number.isRequired,
    data: PropTypes.objectOf(PropTypes.object).isRequired,
    users: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default UserSelectForm;
