import React, { useState, useEffect } from 'react';
import { Dropdown, Input, Header,Image, Container, Menu, Grid, Form, Segment, Loader  } from 'semantic-ui-react'

import finger from '../image/finger.svg';
import RankBox from './RankBox';
import Match from '../match/match';
import pepe_q from '../image/pepe_question.jpg';
import { api } from '../api/index';
import './result.css';
import SearchBar from './SearchBar';
import UserInfo from './UserInfo';

import question from '../image/pepe_question.jpg';
import siba from '../image/siba.png';
import shit1 from '../image/shit1.png';
import shit2 from '../image/shit2.jpg';
import shit3 from '../image/shit3.jpg';

const options = [
    { key: 'KR', text: 'KR', value: 'KR' },
    { key: 'NA', text: 'NA', value: 'NA' },
    { key: 'VIET', text: 'VIET', value: 'VIET' },
]

const resultimg= (average, len)=>{
    if(len==0){
        return [pepe_q, '경기가 부족합니다']
    }
    let score = average/len;

    if(score <=3){
        return[siba, '훌륭한 경기력!....']
    }
    if(score <= 5){
        return[shit1, '분발해라 뒤지기 싫으면']
    }
    if(score <= 7){
        return[shit2, '니 때문에 니 팀이 지는거야']
    }
    return [shit3, '당신은 가망이 없습니다. 제발 롤 삭제해주세요!']

}

var ex_p = {
    "summonerName": "원스타교장샘",
    "champion": "Irelia",
    "level": 11,
    "cs": 145,
    "kills": 1,
    "deaths":5,
    "assists":15,
    "position":"TOP",
    "item0":1055,
    "item6":1055,
    "spell1":4,
    "spell2":14,
    "score":1,
    "win":true,
}
var ex_match=[
    {
        "queueId": 420,
        
        "gameDuration": 11,
        "gameCreation": 11,
        "participants":{
            "1":ex_p,
            "2":ex_p,
            "3":ex_p,
            "4":ex_p,
            "5":ex_p,
            "6":ex_p,
            "7":ex_p,
            "8":ex_p,
            "9":ex_p,
            "10":ex_p,
        },
    
    }
]


const Result = (props) => {

    const [userReady, setUserReady] = useState(0); // -2: error, -1: 없는유저, 0: 로딩중, 1: 정상
    const [matchReady, setMatchReady] = useState(0); // 0: 로딩중, 1: 정상
    const [userName, set_Name] = useState('원스타교장샘');
    const [userLevel, set_Level] = useState('100');
    const [userProfile, set_Profile] = useState('10');
    const [userSoloRank, set_Solo] = useState({'rank':11, 'wins':15, 'losses':3});
    const [userFlexRank, set_Flex] = useState({'rank':11, 'wins':3, 'losses':1});
    const [matches, set_matches] = useState(ex_match);
    const [average, set_av] = useState(0);

    const[inputvalue, setinput] = useState('')
    const[beReady, setReady] = useState(false);

    useEffect(()=>{
        for(var idx=0; idx < ex_match.length; idx++){
            for(var pos=1; pos<=10; pos++){
                if(ex_match[idx]["participants"][String(pos)]==userName){
                    ex_match[idx]["user"]=String(pos);
                    break;
                }
            }
        }

        api.get('/results_user/'+props.match.params.username+'/').then((response)=>{
            if(response.status == 203){
                var result = response.data;
                set_Name(result['user_name']);
                set_Level(result['user_level']);
                set_Profile(result['user_profile']);
                set_Solo(result['solo_rank']);
                set_Flex(result['flex_rank']);
                setUserReady(1);
            }
            else if(response.status == 404){
                setUserReady(-1);
            }
            else{
                setUserReady(-2);
            }
        });
    },[]);

    useEffect(()=>{
        if(userReady==1){
            api.get('/results_match/'+props.match.params.username+'/').then((response)=>{
                var result = response.data;
                for(var idx=0; idx < result.length; idx++){
                    for(var pos=1; pos<=10; pos++){
                        if(result[idx]["participants"][String(pos)]==userName){
                            result[idx]["user"] = String(pos);
                            break;
                        }
                    }
                }
                set_matches(result);
                setMatchReady(1);
            });
        }
    },[userReady]);

    const clickHeader =()=>{
        props.history.push('/home');
    }

     const handleClick =()=>{
        props.history.push(inputvalue);
        setReady(false);
    }

    const handleKey=(e)=>{
        if(e.key=='Enter'){
            props.history.push(inputvalue);
            setReady(false);
        }
    }

    // if (beReady)
    // {
    //     return(
    //         <div>
                
    //             <Grid className='Headerbar'  columns='equal'>
    //                 <Grid.Column  textAlign='right' verticalAlign='middle' only='computer'>
    //                     <Header  className='logo_title_small' onClick={()=>clickHeader()}>
    //                             <Image src={finger}/>
    //                         누구 탓?
    //                     </Header>
    //                 </Grid.Column>
    //                 <Grid.Column verticalAlign='middle'  only='computer'>
    //                     <Input
    //                         label={<Dropdown defaultValue='KR' options={options} />}
    //                         labelPosition='left'
    //                         placeholder='소환사명을 적어주세요!'
    //                         action={{content:'GO!1', onClick: handleClick }}
    //                         size='large'
    //                         className='summoner_search'
    //                         onChange={e=>setinput(e.target.value)}
    //                         onKeyPress={e=>handleKey(e)}
    //                     />
    //                 </Grid.Column>
    //                 <Grid.Column only='computer'/>

    //                 <Grid.Row only='tablet mobile' centered>
    //                     <Header  className='logo_title_small' onClick={()=>clickHeader()}>
    //                             <Image src={finger}/>
    //                         누구 탓?
    //                     </Header>
    //                 </Grid.Row>
    //                 <Grid.Row only='tablet mobile' centered>
    //                     <Input
    //                         label={<Dropdown defaultValue='KR' options={options} />}
    //                         labelPosition='left'
    //                         placeholder='소환사명을 적어주세요!'
    //                         icon = 'search'
    //                         action={{onClick: handleClick }}
    //                         className='summoner_search_mobile'
    //                         onChange={e=>setinput(e.target.value)}
    //                         onKeyPress={e=>handleKey(e)}
    //                     />
    //                 </Grid.Row>
    //             </Grid>

    //             <Container>
                    
    //             <Grid>
    //                 <Grid.Row only='tablet mobile' verticalAlign='middle'>
    //                     <span>
    //                     <img src={'http://ddragon.leagueoflegends.com/cdn/11.3.1/img/profileicon/'+userProfile+'.png'} className='profile_img_mobile'/>
    //                     </span>
    //                     <span>
    //                     <div className='profile_name_mobile'>
    //                         {userName}
    //                     </div>
    //                     <div className='profile_level_mobile'>
    //                         LV. {userLevel}
    //                     </div>
    //                     </span>
                        
    //                 </Grid.Row>
    //             </Grid>


    //             <Segment  className='profile_box'>
    //             <Grid>
                    
    //                 <Grid.Row  only='computer' columns={2}>
    //                     <Grid.Column textAlign='left'>
    //                         <span>
    //                             <span>
    //                             <img src={'http://ddragon.leagueoflegends.com/cdn/11.3.1/img/profileicon/'+userProfile+'.png'} className='profile_img'/>
    //                             </span> 
    //                             <span className='profile_name'>
    //                             <div className='profile_name1'>
    //                                 {userName}
    //                             </div>
    //                             <div className='profile_level'>
    //                                 LV. {userLevel}
    //                             </div>
    //                             </span>
    //                         </span>
    //                     </Grid.Column>
    //                     <Grid.Column textAlign='right'  >
                    
    //                         <RankBox rankinfo={userFlexRank} isSolo={false}/>  
                            
    //                         <RankBox rankinfo={userSoloRank} isSolo={true}/>
                                    
                            
    //                     </Grid.Column>
    //                 </Grid.Row>

    //                 <Grid.Row only='tablet mobile' centered ci   >
                        
                    
    //                         <RankBox rankinfo={userSoloRank} mobile={true} className='mobile_box1' isSolo={true}/>
    //                         <RankBox rankinfo={userFlexRank} mobile={true} className='mobile_box2' isSolo={false}/>
                        

    //                 </Grid.Row>
                
    //             </Grid>

    //             </Segment>
            
                

            
    //                 <h1>분석결과</h1>
    //                 <img className ='resultimg' src={resultimg(average, matches.length)[0]}/>
    //                 <h1>{resultimg(average, matches.length)[1]}</h1>

    //                 {matches.map((match, i) => <Match info={match} key={i}/>)}
    //             </Container>
    //         </div>
    //     )
    // }
    // else
    // {
    //     return(
    //         <div>
    //             <Grid className='Headerbar'  columns='equal'>
    //                 <Grid.Column  textAlign='right' verticalAlign='middle' only='computer'>
    //                     <Header  className='logo_title_small' onClick={()=>clickHeader()}>
    //                             <Image src={finger}/>
    //                         누구 탓?
    //                     </Header>
    //                 </Grid.Column>
    //                 <Grid.Column verticalAlign='middle'  only='computer'>
    //                     <Input
    //                         label={<Dropdown defaultValue='KR' options={options} />}
    //                         labelPosition='left'
    //                         placeholder='소환사명을 적어주세요!'
    //                         action={{content:'GO!', onClick: handleClick }}
    //                         size='large'
    //                         className='summoner_search'
    //                         onChange={e=>setinput(e.target.value)}
    //                         onKeyPress={e=>handleKey(e)}
    //                     />
    //                 </Grid.Column>
    //                 <Grid.Column only='computer'/>

    //                 <Grid.Row only='tablet mobile' centered>
    //                     <Header  className='logo_title_small' onClick={()=>clickHeader()}>
    //                             <Image src={finger}/>
    //                         누구 탓?
    //                     </Header>
    //                 </Grid.Row>
    //                 <Grid.Row only='tablet mobile' centered>
    //                     <Input
    //                         label={<Dropdown defaultValue='KR' options={options} />}
    //                         labelPosition='left'
    //                         placeholder='소환사명을 적어주세요!'
    //                         icon = 'search'
    //                         action={{onClick: handleClick }}
    //                         className='summoner_search_mobile'
    //                         onChange={e=>setinput(e.target.value)}
    //                         onKeyPress={e=>handleKey(e)}
    //                     />
    //                 </Grid.Row>
    //             </Grid>

    //             <br/><br/><br/><br/><br/><br/><br/><br/>
    //             <Loader active inline='centered' className='loading_icon'/>
    //         </div>
    //     )
    // }

    if(userReady == 0){
        return(
            <div>
                <SearchBar/>
                {/* <br/><br/><br/><br/><br/><br/><br/><br/>
                <Loader active inline='centered' className='loading_icon'/> */}
                <UserInfo userName={userName} userLevel={userLevel} userProfile={userProfile} userFlexRank={userFlexRank}
                userSoloRank={userSoloRank}/>

                
                <h1>분석결과</h1>
                <img className ='resultimg' src={resultimg(average, matches.length)[0]}/>
                <h1>{resultimg(average, matches.length)[1]}</h1>

                {ex_match.map((match, i) => <Match info={match} key={i}/>)}
            </div>
        )
    }
    else if(userReady == -2){
        return(
            <div>
                <SearchBar/>
                <br/><br/><br/><br/><br/><br/><br/><br/>
                Error 발생!
            </div>
        )
    }
    else if(userReady == -1){
        return(
            <div>
                <SearchBar/>
                <br/><br/><br/><br/><br/><br/><br/><br/>
                없는 소환사!
            </div>
        )
    }
    else if(userReady == 1 && matchReady == 0){
        return(
            <div>
                <SearchBar/>
                <UserInfo userName={userName} userLevel={userLevel} userProfile={userProfile} userFlexRank={userFlexRank}
                userSoloRank={userSoloRank}/>
                <Loader active inline='centered' className='loading_icon'/>

            </div>
        )
    }
    else if(userReady == 1 && matchReady == 1){
        return(
            <div>
                <SearchBar/>
                <UserInfo userName={userName} userLevel={userLevel} userProfile={userProfile} userFlexRank={userFlexRank}
                userSoloRank={userSoloRank}/>
                
                <h1>분석결과</h1>
                <img className ='resultimg' src={resultimg(average, matches.length)[0]}/>
                <h1>{resultimg(average, matches.length)[1]}</h1>

                {matches.map((match, i) => <Match info={match} key={i}/>)}
            </div>
        )
    }


}

export default Result;