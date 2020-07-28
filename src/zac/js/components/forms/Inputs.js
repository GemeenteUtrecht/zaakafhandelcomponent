import React from "react";


const Input = ({ type='text', id='', name='', initial, classes=null, checked=false, onBlur, onChange, required=false, disabled=false }) => {
    const classNames = classes ??`input__control input__control--${type}`;

    let extraProps = {};
    if (id) {
        extraProps.id = id;
    }

    return (
        <input
            name={name}
            type={type}
            defaultValue={initial || ''}
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


// const TextInput = (props) => {
//     const { label, helpText, id, required } = props;

//     return (
//         <Wrapper>
//             <Label label={label} required={required} idForLabel={id} />
//             <Help helpText={helpText} idForLabel={id} />
//             <ErrorList />
//             <Input type="text" {...props} />
//         </Wrapper>
//     );
// };


// const DateInput = (props) => {
//     return <Input type="date" {...props} />;
// };

const CheckboxInput = (props) => {
    return <Input type="checkbox" {...props} />;
};

const RadioInput = (props) => {
    return <Input type="radio" {...props} />;
};

const HiddenInput = ({name, value}) => {
    return <input type="hidden" name={name} defaultValue={value} />
}


// export {Input, TextInput, DateInput, CheckboxInput, RadioInput, HiddenInput};
export {Input, CheckboxInput, RadioInput, HiddenInput};
