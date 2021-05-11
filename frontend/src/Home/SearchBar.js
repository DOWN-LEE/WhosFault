import React, { useState, useEffect } from 'react';
import { Dropdown, Input, Header,Image, Container, Menu, Grid, Form, Segment, Button  } from 'semantic-ui-react'
import finger from '../image/finger.svg';

import './SearchBar.css';


const options = [
    { key: 'KR', text: 'KR', value: 'KR' },
    { key: 'NA', text: 'NA', value: 'NA' },
    { key: 'VIET', text: 'VIET', value: 'VIET' },
]


const SearchBar = (props) =>{

    const[inputvalue, setinput] = useState('')
  

    const clickHeader =()=>{
        props.history.push('/home');
    }

     const handleClick =()=>{
        props.history.push(inputvalue);
        props.setMatchReady(0);
        props.setUserReady(0);
    }

    const handleKey=(e)=>{
        if(e.key=='Enter'){
            props.history.push(inputvalue);
            props.setMatchReady(0);
            props.setUserReady(0);
        }
    }
    
    return(
        <div>
            <Grid className='Headerbar'  columns='equal'>
                <Grid.Column  textAlign='right' verticalAlign='middle' only='computer'>
                    <Header  className='logo_title_small' onClick={()=>clickHeader()}>
                            <Image src={finger}/>
                        누구 탓?
                    </Header>
                </Grid.Column>
                <Grid.Column verticalAlign='middle'  only='computer'>
                    <Input
                        label={<Dropdown defaultValue='KR' options={options} />}
                        labelPosition='left'
                        placeholder='소환사명을 적어주세요!'
                       
                        size='large'
                        className='summoner_search'
                        onChange={e=>setinput(e.target.value)}
                        onKeyPress={e=>handleKey(e)}
                    />
                </Grid.Column>
                    
                <Grid.Column only='computer' verticalAlign='left'>
                
                </Grid.Column>

                <Grid.Row only='tablet mobile' centered>
                    <Header  className='logo_title_small' onClick={()=>clickHeader()}>
                            <Image src={finger}/>
                        누구 탓?
                    </Header>
                </Grid.Row>
                <Grid.Row only='tablet mobile' centered>
                    <Input
                        label={<Dropdown defaultValue='KR' options={options} />}
                        labelPosition='left'
                        placeholder='소환사명을 적어주세요!'
                        icon = 'search'
                        action={{onClick: handleClick }}
                        className='summoner_search_mobile'
                        onChange={e=>setinput(e.target.value)}
                        onKeyPress={e=>handleKey(e)}
                    />
                </Grid.Row>
            </Grid>

        </div> 
    )
}


export default SearchBar;