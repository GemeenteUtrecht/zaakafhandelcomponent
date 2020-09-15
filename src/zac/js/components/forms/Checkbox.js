import React, { useState } from 'react';
import classnames from 'classnames';
import PropTypes from 'prop-types';

const Checkbox = ({
    onChange,
    value,
    id,
    name,
}) => {
    const [checked, updateChecked] = useState(false);
    return (
        <div
            className={classnames('checkbox-select__checkbox', {
                'checkbox-select__checkbox--checked': checked,
            })}
            onClick={() => updateChecked(!checked)}
        >
            <input
                id={id}
                name={name}
                className="checkbox-select__inner"
                onClick={() => updateChecked(!checked)}
                onChange={(e) => onChange(e)}
                type="checkbox"
                value={value}
            />
        </div>
    );
};

Checkbox.propTypes = {
    onChange: PropTypes.func,
    value: PropTypes.string,
    id: PropTypes.string,
    name: PropTypes.string,
};

export default Checkbox;
