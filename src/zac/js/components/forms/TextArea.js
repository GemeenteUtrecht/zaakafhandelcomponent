import React from 'react';
import PropTypes from 'prop-types';

import { Help } from './Help';
import { Label } from './Label';
import { ErrorList, Wrapper } from './Utils';


const RawTextArea = ({ id='', name='', initial, classes=null, onBlur, onChange, required=false, disabled=false }) => {
    const classNames = classes ?? 'input__control input__control--text';
    return (
        <textarea
            name={name}
            id={id}
            defaultValue={initial || ''}
            className={classNames}
            onBlur={ (event) => {
                if (onBlur) {
                    onBlur(event);
                }
            }}
            onChange={ (event) => {
                if (onChange) {
                    onChange(event);
                }
            }}
            required={required}
            disabled={disabled}
        ></textarea>
    );
};


const TextArea = (props) => {
    const { label, helpText, id, required } = props;
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
