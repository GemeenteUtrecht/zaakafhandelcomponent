import React from 'react';
import PropTypes from 'prop-types';
import Option from './Option';

const Options = ({ options, onChange }) => (
    <div className="checkbox-select__options">
        {options.map((option) => (
            <Option
                onChange={onChange}
                option={option}
                key={option.id}
            />
        ))}
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
};

export default Options;
