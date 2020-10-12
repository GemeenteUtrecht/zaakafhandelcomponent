import React from 'react';
import PropTypes from 'prop-types';
import Checkbox from './Checkbox';

const Options = ({ options, onChange, required }) => (
    <div className="checkbox-select__options">
        {options.map((option) => (
            <Checkbox
                onChange={onChange}
                option={option}
                key={option.id}
            />
        ))}
        {required
        && (
            <div className="input">
                <div className="input__label">
                    <span className="label label--optional">verplicht</span>
                </div>
            </div>
        )}
    </div>
);

Options.propTypes = {
    options: PropTypes.arrayOf(
        PropTypes.shape({
            name: PropTypes.string,
            id: PropTypes.string,
            value: PropTypes.string,
            label: PropTypes.string,
        }),
    ),
    onChange: PropTypes.func,
    required: PropTypes.bool,
};

export default Options;
