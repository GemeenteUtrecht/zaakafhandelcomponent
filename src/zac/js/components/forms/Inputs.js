import React, { useContext, useRef, useState } from 'react';

import { PrefixContext } from '../formsets/context';
import { Help } from './Help';
import { Label } from './Label';
import { ErrorList, Wrapper } from './Utils';



const Input = ({
    type='text',
    id='',
    name='',
    initial=null,
    value='',
    classes=null,
    checked=false,
    onBlur,
    onChange,
    required=false,
    disabled=false,
    ...extraProps
}) => {
    const prefix = useContext(PrefixContext);

    const classNames = classes ??`input__control input__control--${type}`;

    if (id) {
        const prefixedId = prefix ? `${prefix}-${id}` : id;
        extraProps.id = prefixedId;
    }

    // not-controlled vs. controlled
    if (initial != null) {
        extraProps.defaultValue = initial;
    } else {
        extraProps.value = value;
    }

    const prefixedName = prefix ? `${prefix}-${name}` : name;

    return (
        <input
            name={prefixedName}
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


const WrappedInput = ({ type="text", helpText, label, errors=[], ...props }) => {
    const { id, required } = props;
    const prefix = useContext(PrefixContext);
    const prefixedId = (id && prefix) ? `${prefix}-${id}` : id;

    return (
        <Wrapper errors={errors}>
            <Label label={label} required={required} idForLabel={prefixedId} />
            <Help helpText={helpText} idForLabel={prefixedId} />
            <ErrorList errors={errors} />
            <Input type={type} {...props} />
        </Wrapper>
    );
};


const TextInput = (props) => {
    return <WrappedInput type="text" {...props} />
};


const PasswordInput = (props) => {
    return <WrappedInput type="password" {...props} />
};


const DateInput = (props) => {
    return <Input type="date" {...props} />;
};

const CheckboxInput = (props) => {
    return <Input type="checkbox" {...props} />;
};

const HiddenCheckbox = ({name, value}) => {
    const prefix = useContext(PrefixContext);
    const prefixedName = prefix ? `${prefix}-${name}` : name;
    return <input
        type="checkbox"
        className="input input--hidden"
        name={prefixedName}
        value={value}
        key={value}
        defaultChecked
    />
}

const RadioInput = (props) => {
    return <Input type="radio" {...props} />;
};

const HiddenInput = ({name, value}) => {
    const prefix = useContext(PrefixContext);
    const prefixedName = prefix ? `${prefix}-${name}` : name;
    return <input type="hidden" name={prefixedName} value={value}/>
}


const FileInput = ({name, label, helpText, id, required=false, errors=[], multiple=false, onChange, children }) => {
    const fileInput = useRef(null);

    const onInputChange = () => {
        onChange(fileInput.current.files);
    };

    return (
        <Wrapper errors={errors}>
            <Label label={label} required={required} idForLabel={id} />
            <Help helpText={helpText} idForLabel={id} />
            <ErrorList errors={errors} />

            <label>
                <input
                    type="file"
                    id={ id }
                    name={ name }
                    className="input__control input__control--file"
                    multiple={ multiple }
                    ref={ fileInput }
                    onChange={ onInputChange }
                />
                <span className="btn" role="button">Bladeren...</span>
            </label>

            { children ? (<div>{ children }</div>) : null }

        </Wrapper>
    );
};


export {
    Input,
    TextInput,
    DateInput,
    CheckboxInput,
    HiddenCheckbox,
    RadioInput,
    HiddenInput,
    FileInput,
    PasswordInput,
};
