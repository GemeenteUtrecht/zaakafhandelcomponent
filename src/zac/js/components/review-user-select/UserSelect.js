import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Select from 'react-select';
import { getUserName } from '../../utils/users';
import { HiddenCheckbox } from '../forms/Inputs';
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

const UserSelect = ({
    index, totalStepsIndex, data: { values, errors }, users,
}) => {
    const [selectedData, setSelectedData] = useState(null);
    const [hiddenInputs, setHiddenInputs] = useState(null);

    // Default hidden input for the form
    const DefaultHiddenCheckbox = () => (
        <input type="checkbox" className="input input--hidden" name={`form-${index}-kownsl_users`} required />
    );

    // Create hidden inputs of the selected users
    const getHiddenInputs = (selectedUsers) => {
        const inputs = selectedUsers
            ? selectedUsers.map((user) => <HiddenCheckbox name="kownsl_users" value={user.value} key={user.value} required />)
            : DefaultHiddenCheckbox;
        setHiddenInputs(inputs);
    };

    const handleSelectChange = (value) => {
        setSelectedData(value);
    };

    useEffect(() => {
        getHiddenInputs(selectedData);
    }, [selectedData]);

    const StepTitle = totalStepsIndex !== 0 ? <h3>{`Stap ${index + 1}`}</h3> : <h3> </h3>;

    return (
        <div className="user-select" style={{ position: 'relative' }}>
            { (errors && !isEmpty(errors.__all__))
                ? (
                    <Wrapper errors={errors.__all__}>
                        <ErrorList errors={extractErrors(errors.__all__)} />
                    </Wrapper>
                ) : null}

            {StepTitle}
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
        </div>
    );
};

UserSelect.propTypes = {
    index: PropTypes.number.isRequired,
    totalStepsIndex: PropTypes.number,
    data: PropTypes.objectOf(PropTypes.object).isRequired,
    users: PropTypes.arrayOf(PropTypes.object).isRequired,
};

export default UserSelect;
