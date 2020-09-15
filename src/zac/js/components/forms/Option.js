import React from 'react';
import PropTypes from 'prop-types';
import Checkbox from './Checkbox';

const Option = ({ option, onChange }) => (
    <div className="checkbox-select__option">
        <Checkbox value={option.value} id={option.id} name={option.name} onChange={onChange} />
        <label htmlFor={option.id}>{option.label}</label>
    </div>
);

Option.propTypes = {
    onChange: PropTypes.func,
    option: PropTypes.shape(
        {
            value: PropTypes.string,
            id: PropTypes.string,
            name: PropTypes.string,
            label: PropTypes.string,
        },
    ),
};

export default Option;
