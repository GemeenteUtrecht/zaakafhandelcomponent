import React from 'react';
import PropTypes from 'prop-types';

import { Help } from './Help';
import { Label } from './Label';
import { ErrorList, Wrapper } from './Utils';

const RawTextArea = ({
    id = '',
    name = '',
    initial = '',
    value = '',
    classes = null,
    onBlur,
    onChange,
    required = false,
    disabled = false,
}) => {
    const classNames = classes || 'input__control input__control--textarea';

    const extraProps = {};
    if (id) {
        extraProps.id = id;
    }
    // not-controlled vs. controlled
    if (initial) {
        extraProps.defaultValue = initial;
    } else {
        extraProps.value = value;
    }

    return (
        <textarea
            name={name}
            className={classNames}
            onBlur={(event) => {
                if (onBlur) {
                    onBlur(event);
                }
            }}
            onChange={(event) => {
                if (onChange) {
                    onChange(event);
                }
            }}
            required={required}
            disabled={disabled}
            {...extraProps}
        />
    );
};

const TextArea = (props) => {
    const {
        label, helpText, id, required,
    } = props;
    return (
        <Wrapper>
            <Label label={label} required={required} idForLabel={id} />
            <Help helpText={helpText} idForLabel={id} />
            <ErrorList />
            <RawTextArea {...props} />
        </Wrapper>
    );
};

TextArea.propTypes = {
    name: PropTypes.string.isRequired,
    label: PropTypes.string,
    required: PropTypes.bool,
    id: PropTypes.string,
    helpText: PropTypes.string,
};

export { TextArea };
