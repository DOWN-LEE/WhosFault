import React, { useState, useEffect } from 'react';
import { Dropdown, Input, Header,Image,Container  } from 'semantic-ui-react'
import './Home.css';

import finger from '../image/finger.svg';
import pepe_q from '../image/pepe_question.jpg';

const options = [
    { key: 'KR', text: 'KR', value: 'KR' },
    { key: 'NA', text: 'NA', value: 'NA' },
    { key: 'VIET', text: 'VIET', value: 'VIET' },
]


const MainPage = (props) => {
    const[inputvalue, setinput] = useState('')

    const handleClick =()=>{
        props.history.push('result/'+inputvalue);
    }

    const handleKey=(e)=>{
        if(e.key=='Enter'){
            props.history.push('result/'+inputvalue);
        }
    }

    return(
        <div>
            <br/>
            <Header  className='logo_title'>
                <Image src={finger}/>
                누구 탓?
            </Header>
            <Input
                label={<Dropdown defaultValue='KR' options={options} />}
                labelPosition='left'
                placeholder='소환사명을 적어주세요!'
                action={{content:'GO!', onClick: handleClick }}
                size='large'
                className='summoner_search'
                onChange={e=>setinput(e.target.value)}
                onKeyPress={e=>handleKey(e)}
            />

            <br/> <br/> <br/> <br/> <br/>
            <div className='pepe_q'>
                <Image src={pepe_q} className='pepe_q'/>
                <Header>승급 못하는 이유는 팀탓? 내탓?</Header>
            </div>
        </div>
    )
}

export default MainPage;