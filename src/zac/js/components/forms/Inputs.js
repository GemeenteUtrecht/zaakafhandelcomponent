import React from 'react';

import { Help } from './Help';
import { Label } from './Label';
import { ErrorList, Wrapper } from './Utils';


const Input = ({
    type='text',
    id='',
    name='',
    initial='',
    value='',
    classes=null,
    checked=false,
    onBlur,
    onChange,
    required=false,
    disabled=false
}) => {

    const classNames = classes ??`input__control input__control--${type}`;

    let extraProps = {};
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
        <input
            name={name}
            type={type}
            checked={checked}
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
            {...extraProps}
        ></input>
    );
};


const TextInput = (props) => {
    const { label, helpText, id, required, errors=[] } = props;

    return (
        <Wrapper errors={errors}>
            <Label label={label} required={required} idForLabel={id} />
            <Help helpText={helpText} idForLabel={id} />
            <ErrorList errors={errors} />
            <Input type="text" {...props} />
        </Wrapper>
    );
};


const DateInput = (props) => {
    return <Input type="date" {...props} />;
};

const CheckboxInput = (props) => {
    return <Input type="checkbox" {...props} />;
};

const RadioInput = (props) => {
    return <Input type="radio" {...props} />;
};

const HiddenInput = ({name, value}) => {
    return <input type="hidden" name={name} defaultValue={value} />
}


export {Input, TextInput, DateInput, CheckboxInput, RadioInput, HiddenInput};
