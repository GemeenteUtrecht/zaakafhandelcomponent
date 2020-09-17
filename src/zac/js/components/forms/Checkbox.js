import React, { useState } from 'react';
import PropTypes from 'prop-types';

const Checkbox = ({ option, onChange }) => {
    const [checked, updateChecked] = useState(false);

    return (
        <div
            className="checkbox-select__checkbox"
            onClick={() => updateChecked(!checked)}
        >
            <input
                id={option.id}
                name={option.name}
                onChange={(e) => onChange(e)}
                type="checkbox"
                value={option.value}
            />
            <label
                className="checkbox-select__label"
                htmlFor={option.id}
            >
                {option.label}
            </label>
        </div>
    );
};

Checkbox.propTypes = {
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

export default Checkbox;
